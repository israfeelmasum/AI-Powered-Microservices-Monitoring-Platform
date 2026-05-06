# monitoring-core/app/ai/pattern_analyzer.py
import logging
from typing import List, Dict, Any
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import json
import numpy as np

logger = logging.getLogger(__name__)


class PatternAnalyzer:
    """AI-powered pattern recognition for log analysis"""

    def __init__(self, ollama_client):
        self.ollama = ollama_client

    async def analyze_patterns(self, logs: List[Dict], time_window_hours: int = 24) -> Dict[str, Any]:
        """Analyze patterns in log data"""
        try:
            # Basic pattern analysis
            basic_patterns = self._analyze_basic_patterns(logs)

            # AI-powered deep pattern analysis
            ai_patterns = await self._ai_pattern_analysis(logs, basic_patterns)

            return {
                "timestamp": datetime.utcnow().isoformat(),
                "time_window_hours": time_window_hours,
                "log_count": len(logs),
                "basic_patterns": basic_patterns,
                "ai_insights": ai_patterns,
                "pattern_score": self._calculate_pattern_score(basic_patterns, ai_patterns)
            }

        except Exception as e:
            logger.error(f"Pattern analysis error: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}

    def _analyze_basic_patterns(self, logs: List[Dict]) -> Dict[str, Any]:
        """Analyze basic patterns in logs"""
        patterns = {
            "temporal_patterns": self._analyze_temporal_patterns(logs),
            "service_patterns": self._analyze_service_patterns(logs),
            "error_patterns": self._analyze_error_patterns(logs),
            "endpoint_patterns": self._analyze_endpoint_patterns(logs),
            "user_patterns": self._analyze_user_patterns(logs)
        }
        return patterns

    def _analyze_temporal_patterns(self, logs: List[Dict]) -> Dict[str, Any]:
        """Analyze temporal patterns in logs"""
        hourly_counts = defaultdict(int)
        daily_counts = defaultdict(int)

        for log in logs:
            try:
                timestamp = datetime.fromisoformat(log.get("timestamp", "").replace('Z', '+00:00'))
                hour = timestamp.hour
                day = timestamp.strftime('%Y-%m-%d')
                hourly_counts[hour] += 1
                daily_counts[day] += 1
            except:
                continue

        # Find peak and quiet hours
        sorted_hours = sorted(hourly_counts.items(), key=lambda x: x[1], reverse=True)

        return {
            "hourly_distribution": dict(hourly_counts),
            "daily_distribution": dict(daily_counts),
            "peak_hours": sorted_hours[:3] if sorted_hours else [],
            "quiet_hours": sorted_hours[-3:] if sorted_hours else [],
            "total_active_hours": len(hourly_counts),
            "avg_logs_per_hour": np.mean(list(hourly_counts.values())) if hourly_counts else 0
        }

    def _analyze_service_patterns(self, logs: List[Dict]) -> Dict[str, Any]:
        """Analyze service-related patterns"""
        service_stats = defaultdict(lambda: {
            "total": 0,
            "errors": 0,
            "response_times": [],
            "endpoints": set(),
            "error_types": defaultdict(int)
        })

        for log in logs:
            service = log.get("service", "unknown")
            service_stats[service]["total"] += 1

            if log.get("level") in ["ERROR", "CRITICAL"]:
                service_stats[service]["errors"] += 1
                error_type = log.get("error_type", "unknown")
                service_stats[service]["error_types"][error_type] += 1

            if "response_time" in log and log["response_time"] is not None:
                service_stats[service]["response_times"].append(log["response_time"])

            if "endpoint" in log:
                service_stats[service]["endpoints"].add(log["endpoint"])

        # Calculate service metrics
        service_summary = {}
        for service, stats in service_stats.items():
            response_times = stats["response_times"]
            avg_response = np.mean(response_times) if response_times else 0
            p95_response = np.percentile(response_times, 95) if response_times else 0
            error_rate = (stats["errors"] / stats["total"]) * 100 if stats["total"] > 0 else 0

            service_summary[service] = {
                "total_requests": stats["total"],
                "error_count": stats["errors"],
                "error_rate_percent": round(error_rate, 2),
                "avg_response_time_ms": round(avg_response, 2),
                "p95_response_time_ms": round(p95_response, 2),
                "unique_endpoints": len(stats["endpoints"]),
                "health_score": max(0, 100 - error_rate - (avg_response / 1000 * 10)),
                "top_error_types": dict(Counter(stats["error_types"]).most_common(3))
            }

        return service_summary

    def _analyze_error_patterns(self, logs: List[Dict]) -> Dict[str, Any]:
        """Analyze error patterns"""
        error_logs = [log for log in logs if log.get("level") in ["ERROR", "CRITICAL"]]

        if not error_logs:
            return {"no_errors": True, "total_errors": 0}

        # Group errors by different dimensions
        error_by_service = defaultdict(int)
        error_by_type = defaultdict(int)
        error_by_endpoint = defaultdict(int)
        error_messages = []

        for log in error_logs:
            service = log.get("service", "unknown")
            error_type = log.get("error_type", "unknown")
            endpoint = log.get("endpoint", "unknown")
            message = log.get("message", "")

            error_by_service[service] += 1
            error_by_type[error_type] += 1
            error_by_endpoint[endpoint] += 1

            # Categorize error messages
            message_lower = message.lower()
            if "timeout" in message_lower:
                error_by_type["timeout"] += 1
            elif "connection" in message_lower:
                error_by_type["connection"] += 1
            elif "permission" in message_lower or "unauthorized" in message_lower:
                error_by_type["authorization"] += 1
            elif "not found" in message_lower or "404" in message:
                error_by_type["not_found"] += 1
            elif "internal server error" in message_lower or "500" in message:
                error_by_type["server_error"] += 1

            error_messages.append({
                "message": message[:200],
                "service": service,
                "timestamp": log.get("timestamp")
            })

        return {
            "total_errors": len(error_logs),
            "error_rate_per_hour": len(error_logs) / 24,  # Assuming 24h window
            "errors_by_service": dict(error_by_service),
            "errors_by_type": dict(error_by_type),
            "errors_by_endpoint": dict(error_by_endpoint),
            "most_common_errors": dict(Counter(error_by_type).most_common(5)),
            "recent_error_messages": error_messages[:10]
        }

    def _analyze_endpoint_patterns(self, logs: List[Dict]) -> Dict[str, Any]:
        """Analyze API endpoint patterns"""
        endpoint_stats = defaultdict(lambda: {
            "count": 0,
            "response_times": [],
            "errors": 0,
            "methods": defaultdict(int),
            "status_codes": defaultdict(int)
        })

        for log in logs:
            endpoint = log.get("endpoint")
            if endpoint:
                endpoint_stats[endpoint]["count"] += 1

                if "response_time" in log and log["response_time"] is not None:
                    endpoint_stats[endpoint]["response_times"].append(log["response_time"])

                if log.get("level") in ["ERROR", "CRITICAL"]:
                    endpoint_stats[endpoint]["errors"] += 1

                method = log.get("method", "unknown")
                endpoint_stats[endpoint]["methods"][method] += 1

                status_code = log.get("status_code")
                if status_code:
                    endpoint_stats[endpoint]["status_codes"][str(status_code)] += 1

        # Calculate endpoint metrics
        endpoint_summary = {}
        for endpoint, stats in endpoint_stats.items():
            response_times = stats["response_times"]
            avg_response = np.mean(response_times) if response_times else 0
            p95_response = np.percentile(response_times, 95) if response_times else 0
            error_rate = (stats["errors"] / stats["count"]) * 100 if stats["count"] > 0 else 0

            endpoint_summary[endpoint] = {
                "request_count": stats["count"],
                "avg_response_time_ms": round(avg_response, 2),
                "p95_response_time_ms": round(p95_response, 2),
                "error_rate_percent": round(error_rate, 2),
                "requests_per_hour": stats["count"] / 24,
                "most_common_method": max(stats["methods"], key=stats["methods"].get) if stats[
                    "methods"] else "unknown",
                "status_code_distribution": dict(stats["status_codes"])
            }

        # Find top endpoints by different metrics
        top_by_traffic = sorted(endpoint_summary.items(), key=lambda x: x[1]["request_count"], reverse=True)[:10]
        top_by_errors = sorted(endpoint_summary.items(), key=lambda x: x[1]["error_rate_percent"], reverse=True)[:10]
        top_by_response_time = sorted(endpoint_summary.items(), key=lambda x: x[1]["avg_response_time_ms"],
                                      reverse=True)[:10]

        return {
            "total_unique_endpoints": len(endpoint_summary),
            "top_endpoints_by_traffic": dict(top_by_traffic),
            "top_endpoints_by_errors": dict(top_by_errors),
            "top_endpoints_by_response_time": dict(top_by_response_time),
            "endpoint_summary": endpoint_summary
        }

    def _analyze_user_patterns(self, logs: List[Dict]) -> Dict[str, Any]:
        """Analyze user activity patterns"""
        user_activities = defaultdict(int)
        ip_activities = defaultdict(int)
        user_agents = defaultdict(int)

        for log in logs:
            user_id = log.get("user_id")
            client_ip = log.get("client_ip")
            user_agent = log.get("user_agent", "")

            if user_id:
                user_activities[user_id] += 1

            if client_ip and client_ip != "unknown":
                ip_activities[client_ip] += 1

            if user_agent and len(user_agent) > 5:  # Filter out empty/short user agents
                # Extract browser/application from user agent
                ua_lower = user_agent.lower()
                if "chrome" in ua_lower:
                    user_agents["Chrome"] += 1
                elif "firefox" in ua_lower:
                    user_agents["Firefox"] += 1
                elif "safari" in ua_lower:
                    user_agents["Safari"] += 1
                elif "curl" in ua_lower:
                    user_agents["curl"] += 1
                elif "postman" in ua_lower:
                    user_agents["Postman"] += 1
                else:
                    user_agents["Other"] += 1

        result = {
            "unique_users": len(user_activities),
            "unique_ips": len(ip_activities),
            "total_user_activities": sum(user_activities.values()),
            "avg_activities_per_user": sum(user_activities.values()) / len(user_activities) if user_activities else 0,
            "top_active_users": dict(Counter(user_activities).most_common(10)),
            "top_active_ips": dict(Counter(ip_activities).most_common(10)),
            "user_agent_distribution": dict(user_agents)
        }

        if not user_activities and not ip_activities:
            result["no_user_data"] = True

        return result

    async def _ai_pattern_analysis(self, logs: List[Dict], basic_patterns: Dict) -> Dict[str, Any]:
        """AI-powered deep pattern analysis"""
        try:
            prompt = self._create_pattern_analysis_prompt(basic_patterns)
            result = await self.ollama.generate(prompt, model="mistral")

            if result["success"]:
                return self._parse_ai_pattern_response(result["response"])
            else:
                return {"ai_analysis_failed": True, "error": result.get("error")}

        except Exception as e:
            logger.error(f"AI pattern analysis error: {e}")
            return {"ai_analysis_failed": True, "error": str(e)}

    def _create_pattern_analysis_prompt(self, basic_patterns: Dict) -> str:
        """Create prompt for AI pattern analysis"""
        return f"""
Analyze the following system monitoring patterns and provide insights:

TEMPORAL PATTERNS:
{json.dumps(basic_patterns.get('temporal_patterns', {}), indent=2)}

SERVICE PATTERNS:
{json.dumps(basic_patterns.get('service_patterns', {}), indent=2)}

ERROR PATTERNS:
{json.dumps(basic_patterns.get('error_patterns', {}), indent=2)}

ENDPOINT PATTERNS:
{json.dumps(basic_patterns.get('endpoint_patterns', {}), indent=2)}

USER PATTERNS:
{json.dumps(basic_patterns.get('user_patterns', {}), indent=2)}

Please provide:
1. Key insights from the patterns
2. Potential issues or concerns
3. Optimization recommendations
4. Predicted trends
5. Risk assessment (low/medium/high)

Format response as JSON with keys: insights, issues, recommendations, trends, risk_level
"""

    def _parse_ai_pattern_response(self, ai_response: str) -> Dict[str, Any]:
        """Parse AI pattern analysis response"""
        try:
            start_idx = ai_response.find('{')
            end_idx = ai_response.rfind('}') + 1

            if start_idx >= 0 and end_idx > start_idx:
                json_str = ai_response[start_idx:end_idx]
                return json.loads(json_str)
            else:
                return {"raw_response": ai_response}

        except json.JSONDecodeError:
            return {"raw_response": ai_response}

    def _calculate_pattern_score(self, basic_patterns: Dict, ai_patterns: Dict) -> float:
        """Calculate overall pattern health score"""
        score = 100.0

        # Deduct points for errors
        error_patterns = basic_patterns.get("error_patterns", {})
        if not error_patterns.get("no_errors", False):
            error_count = error_patterns.get("total_errors", 0)
            score -= min(50, error_count * 2)  # Max 50 points deduction for errors

        # Deduct points for poor service performance
        service_patterns = basic_patterns.get("service_patterns", {})
        for service_data in service_patterns.values():
            error_rate = service_data.get("error_rate_percent", 0)
            score -= min(20, error_rate)  # Deduct up to 20 points per service

        # Factor in AI risk assessment
        if "risk_level" in ai_patterns:
            risk_level = ai_patterns["risk_level"].lower() if isinstance(ai_patterns["risk_level"], str) else "medium"
            if risk_level == "high":
                score -= 30
            elif risk_level == "medium":
                score -= 15
            elif risk_level == "critical":
                score -= 50

        return max(0, min(100, score))