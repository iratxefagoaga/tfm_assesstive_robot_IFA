#pragma once

#include <chrono>
#include <functional>
#include <fstream>
#include <map>
#include <memory>
#include <mutex>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

#include "ament_index_cpp/get_package_share_directory.hpp"
#include "lifecycle_msgs/srv/get_state.hpp"
#include "rclcpp/rclcpp.hpp"

namespace wheelchair_assistive_bt
{
inline std::vector<std::string> required_nav2_nodes()
{
  const auto path = ament_index_cpp::get_package_share_directory("wheelchair_navigation") +
    "/config/required_nav2_nodes.txt";
  std::ifstream input(path);
  if (!input) throw std::runtime_error("Cannot read canonical Nav2 node list");
  std::vector<std::string> nodes;
  std::set<std::string> unique;
  std::string line;
  while (std::getline(input, line)) {
    const auto begin = line.find_first_not_of(" \t\r");
    if (begin == std::string::npos) continue;
    const auto name = line.substr(begin, line.find_last_not_of(" \t\r") - begin + 1);
    if (!unique.insert(name).second) throw std::runtime_error("Duplicate required Nav2 node");
    nodes.push_back(name);
  }
  if (nodes.empty()) throw std::runtime_error("Empty canonical Nav2 node list");
  return nodes;
}

// A single bounded round. A completed round grants only its immediately following send.
// Transport injection allows deterministic tests of this same implementation.
class Nav2ReadinessCheck
{
public:
  using Clock = std::chrono::steady_clock;
  enum class Status {CHECKING, ALLOWED, DENIED};
  using Reply = std::function<void(int, const std::string &)>;
  using Cancel = std::function<void()>;
  using Dispatch = std::function<Cancel(const std::string &, Reply)>;
  using Now = std::function<Clock::time_point()>;

  explicit Nav2ReadinessCheck(rclcpp::Node * node)
  : Nav2ReadinessCheck(make_dispatch(node)) {}

  explicit Nav2ReadinessCheck(Dispatch dispatch, Now now = [] {return Clock::now();})
  : nodes_(required_nav2_nodes()), dispatch_(std::move(dispatch)), now_(std::move(now)) {}

  ~Nav2ReadinessCheck() {reset();}
  Nav2ReadinessCheck(const Nav2ReadinessCheck &) = delete;
  Nav2ReadinessCheck & operator=(const Nav2ReadinessCheck &) = delete;

  void begin(std::chrono::milliseconds timeout)
  {
    reset();
    state_ = std::make_shared<Round>();
    state_->deadline = now_() + timeout;
    for (const auto & name : nodes_) state_->pending.insert(name);
    dispatch_pending();
  }

  Status poll()
  {
    if (!state_) return Status::DENIED;
    {
      std::lock_guard<std::mutex> lock(state_->mutex);
      if (state_->status == Status::CHECKING && now_() >= state_->deadline) {
        state_->status = Status::DENIED;
        state_->reason = "/" + *state_->pending.begin() + "/get_state: response timeout";
      }
    }
    if (status() == Status::CHECKING) dispatch_pending();
    const auto current = status();
    if (current != Status::CHECKING) cancel_pending();
    return current;
  }

  std::string reason() const
  {
    if (!state_) return "Readiness round not started";
    std::lock_guard<std::mutex> lock(state_->mutex);
    return state_->reason;
  }

  void reset()
  {
    if (state_) {
      std::lock_guard<std::mutex> lock(state_->mutex);
      state_->status = Status::DENIED;
    }
    cancel_pending();
    state_.reset();
  }

private:
  Status status() const
  {
    if (!state_) return Status::DENIED;
    std::lock_guard<std::mutex> lock(state_->mutex);
    return state_->status;
  }

  void dispatch_pending()
  {
    const auto state = state_;
    if (!state) return;
    std::vector<std::string> ready_to_dispatch;
    {
      std::lock_guard<std::mutex> lock(state->mutex);
      if (state->status != Status::CHECKING) return;
      for (const auto & name : state->pending) {
        if (state->in_flight.insert(name).second) ready_to_dispatch.push_back(name);
      }
    }
    const std::weak_ptr<Round> weak = state_;
    for (const auto & name : ready_to_dispatch) {
      try {
        auto cancel = dispatch_(name, [weak, name, now = now_](int id, const std::string & error) {
          if (auto state = weak.lock()) {
            std::lock_guard<std::mutex> lock(state->mutex);
            state->in_flight.erase(name);
            if (state->status != Status::CHECKING || !state->pending.count(name)) return;
            // Service discovery can lag process startup. Keep the node pending
            // and retry on the next existing BT tick until this round's deadline.
            if (error == "service unavailable") return;
            state->pending.erase(name);
            if (now() >= state->deadline) {
              state->status = Status::DENIED;
              state->reason = "/" + name + "/get_state: response timeout";
            } else if (!error.empty() || id != 3) {
              state->status = Status::DENIED;
              state->reason = "/" + name + "/get_state: " +
                (error.empty() ? "state=" + std::to_string(id) + " (expected ACTIVE)" : error);
            } else if (state->pending.empty()) {
              state->status = Status::ALLOWED;
            }
          }
        });
        if (cancel) cancellations_.push_back(std::move(cancel));
      } catch (const std::exception & error) {
        {
          std::lock_guard<std::mutex> lock(state->mutex);
          state->in_flight.erase(name);
        }
        deny("/" + name + "/get_state: " + error.what());
      }
    }
  }
  struct Round
  {
    std::mutex mutex;
    Status status{Status::CHECKING};
    std::set<std::string> pending;
    std::set<std::string> in_flight;
    std::string reason;
    Clock::time_point deadline;
  };

  static Dispatch make_dispatch(rclcpp::Node * node)
  {
    using Service = lifecycle_msgs::srv::GetState;
    auto clients = std::make_shared<std::map<std::string, rclcpp::Client<Service>::SharedPtr>>();
    for (const auto & name : required_nav2_nodes()) {
      (*clients)[name] = node->create_client<Service>("/" + name + "/get_state");
    }
    return [clients](const std::string & name, Reply reply) -> Cancel {
      const auto client = clients->at(name);
      if (!client->service_is_ready()) {
        reply(-1, "service unavailable");
        return {};
      }
      auto pending = client->async_send_request(std::make_shared<Service::Request>(),
        [reply](rclcpp::Client<Service>::SharedFuture future) {
          try {
            const auto response = future.get();
            if (!response) reply(-1, "null response");
            else reply(response->current_state.id, "");
          } catch (const std::exception & error) {
            reply(-1, error.what());
          }
        });
      const auto id = pending.request_id;
      return [client, id] {client->remove_pending_request(id);};
    };
  }

  void deny(const std::string & reason)
  {
    std::lock_guard<std::mutex> lock(state_->mutex);
    if (state_->status != Status::CHECKING) return;
    state_->status = Status::DENIED;
    state_->reason = reason;
  }

  void cancel_pending()
  {
    auto cancellations = std::move(cancellations_);
    cancellations_.clear();
    for (const auto & cancel : cancellations) if (cancel) cancel();
  }

  std::vector<std::string> nodes_;
  Dispatch dispatch_;
  Now now_;
  std::shared_ptr<Round> state_;
  std::vector<Cancel> cancellations_;
};
}  // namespace wheelchair_assistive_bt
