# monitoring-core/app/ai/ollama_client.py
import aiohttp
import asyncio
import logging
from typing import List, Dict, Any, Optional
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for Ollama API integration"""

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.session = None
        self.available_models = []

    async def initialize(self):
        """Initialize Ollama client and check available models"""
        self.session = aiohttp.ClientSession()
        await self.check_connection()
        await self.load_available_models()

    async def close(self):
        """Close the HTTP session"""
        if self.session:
            await self.session.close()

    async def check_connection(self) -> bool:
        """Check if Ollama is available"""
        try:
            async with self.session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    logger.info("Ollama connection successful")
                    return True
                else:
                    logger.warning(f"Ollama responded with status: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            return False

    async def load_available_models(self):
        """Load list of available models"""
        try:
            async with self.session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    self.available_models = [model['name'] for model in data.get('models', [])]
                    logger.info(f"Available models: {self.available_models}")
                else:
                    logger.warning("Could not load available models")
        except Exception as e:
            logger.error(f"Error loading models: {e}")

    async def generate(self,
                       prompt: str,
                       model: str = "mistral",
                       context: Optional[str] = None) -> Dict[str, Any]:
        """Generate response using Ollama"""
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Lower temperature for more focused responses
                    "top_p": 0.9,
                    "max_tokens": 1000
                }
            }

            if context:
                payload["context"] = context

            async with self.session.post(
                    f"{self.base_url}/api/generate",
                    json=payload
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "success": True,
                        "response": result.get("response", ""),
                        "model": model,
                        "timestamp": datetime.utcnow()
                    }
                else:
                    error_text = await response.text()
                    logger.error(f"Ollama API error: {response.status} - {error_text}")
                    return {
                        "success": False,
                        "error": f"API error: {response.status}",
                        "timestamp": datetime.utcnow()
                    }

        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow()
            }


# monitoring-core/app/ai/anomaly_detector.py
import json
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """AI-powered anomaly detection using Ollama"""

    def __init__(self, ollama_client):
        self.ollama = ollama_client

    async def detect_anomalies(self, logs: List[Dict]) -> List[Dict]:
        """Detect anomalies in log data using AI"""
        if not logs:
            return []

        try:
            # Prepare log data for analysis
            log_summary = self._prepare_log_summary(logs)

            # Create AI prompt for anomaly detection
            prompt = self._create_anomaly_prompt(log_summary)

            # Get AI analysis
            result = await self.ollama.generate(prompt, model="mistral")

            if result["success"]:
                anomalies = self._parse_anomaly_response(result["response"], logs)
                return anomalies
            else:
                logger.error(f"Anomaly detection failed: {result.get('error')}")
                return []

        except Exception as e:
            logger.error(f"Anomaly detection error: {e}")
            return []

    def _prepare_log_summary(self, logs: List[Dict]) -> Dict:
        """Prepare a summary of logs for AI analysis"""
        summary = {
            "total_logs": len(logs),
            "time_range": {
                "start": min(log.get("timestamp", "") for log in logs),
                "end": max(log.get("timestamp", "") for log in logs)
            },
            "log_levels": {},
            "services": {},
            "error_patterns": [],
            "response_times": [],
            "endpoints": {}
        }

        # Analyze log patterns
        for log in logs:
            # Count log levels
            level = log.get("level", "unknown")
            summary["log_levels"][level] = summary["log_levels"].get(level, 0) + 1

            # Count services
            service = log.get("service", "unknown")
            summary["services"][service] = summary["services"].get(service, 0) + 1

            # Collect error patterns
            if level in ["ERROR", "CRITICAL"]:
                summary["error_patterns"].append({
                    "message": log.get("message", "")[:200],  # Truncate long messages
                    "service": service,
                    "timestamp": log.get("timestamp")
                })

            # Collect response times
            if "response_time" in log:
                summary["response_times"].append(log["response_time"])

            # Count endpoints
            if "endpoint" in log:
                endpoint = log["endpoint"]
                summary["endpoints"][endpoint] = summary["endpoints"].get(endpoint, 0) + 1

        return summary

    def _create_anomaly_prompt(self, log_summary: Dict) -> str:
        """Create AI prompt for anomaly detection"""
        return f"""
Analyze the following system logs and identify potential anomalies or issues:

LOG SUMMARY:
- Total logs: {log_summary['total_logs']}
- Time range: {log_summary['time_range']['start']} to {log_summary['time_range']['end']}
- Log levels: {json.dumps(log_summary['log_levels'], indent=2)}
- Services: {json.dumps(log_summary['services'], indent=2)}
- Recent errors: {json.dumps(log_summary['error_patterns'][:10], indent=2)}
- Response times: Average: {sum(log_summary['response_times']) / len(log_summary['response_times']) if log_summary['response_times'] else 0:.2f}ms
- Top endpoints: {json.dumps(dict(list(log_summary['endpoints'].items())[:10]), indent=2)}

Please analyze this data and identify:
1. Unusual patterns or spikes in errors
2. Performance anomalies (slow response times)
3. Suspicious activity patterns
4. Service health issues
5. Any other notable anomalies

For each anomaly found, provide:
- Type: (error_spike, performance_issue, suspicious_activity, service_issue, other)
- Severity: (low, medium, high, critical)
- Description: Brief explanation
- Affected_services: List of services
- Recommendation: What action should be taken

Format your response as JSON with an "anomalies" array containing the detected issues.
"""

    def _parse_anomaly_response(self, ai_response: str, original_logs: List[Dict]) -> List[Dict]:
        """Parse AI response and create anomaly records"""
        try:
            # Try to extract JSON from AI response
            start_idx = ai_response.find('{')
            end_idx = ai_response.rfind('}') + 1

            if start_idx >= 0 and end_idx > start_idx:
                json_str = ai_response[start_idx:end_idx]
                parsed_response = json.loads(json_str)

                anomalies = []
                for anomaly_data in parsed_response.get("anomalies", []):
                    anomaly = {
                        "id": f"anomaly_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{len(anomalies)}",
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": anomaly_data.get("type", "unknown"),
                        "severity": anomaly_data.get("severity", "medium"),
                        "description": anomaly_data.get("description", ""),
                        "affected_services": anomaly_data.get("affected_services", []),
                        "recommendation": anomaly_data.get("recommendation", ""),
                        "detected_by": "ollama_ai",
                        "model": "mistral",
                        "log_count": len(original_logs)
                    }
                    anomalies.append(anomaly)

                return anomalies
            else:
                logger.warning("Could not extract JSON from AI response")
                return []

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            # Fallback: create a single anomaly based on basic heuristics
            return self._fallback_anomaly_detection(original_logs)
        except Exception as e:
            logger.error(f"Error parsing anomaly response: {e}")
            return []

    def _fallback_anomaly_detection(self, logs: List[Dict]) -> List[Dict]:
        """Fallback anomaly detection using simple heuristics"""
        anomalies = []

        # Count errors
        error_count = sum(1 for log in logs if log.get("level") in ["ERROR", "CRITICAL"])

        if error_count > len(logs) * 0.1:  # More than 10% errors
            anomalies.append({
                "id": f"fallback_error_spike_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                "timestamp": datetime.utcnow().isoformat(),
                "type": "error_spike",
                "severity": "high",
                "description": f"High error rate detected: {error_count} errors in {len(logs)} logs",
                "affected_services": list(
                    set(log.get("service", "unknown") for log in logs if log.get("level") in ["ERROR", "CRITICAL"])),
                "recommendation": "Investigate error causes and implement fixes",
                "detected_by": "fallback_heuristic",
                "model": "rule_based",
                "log_count": len(logs)
            })

        return anomalies


# monitoring-core/app/ai/pattern_analyzer.py
import logging
from typing import List, Dict, Any
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import json

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

        for log in logs:
            try:
                timestamp = datetime.fromisoformat(log.get("timestamp", "").replace('Z', '+00:00'))
                hour = timestamp.hour
                hourly_counts[hour] += 1
            except:
                continue

        # Find peak hours
        sorted_hours = sorted(hourly_counts.items(), key=lambda x: x[1], reverse=True)

        return {
            "hourly_distribution": dict(hourly_counts),
            "peak_hours": sorted_hours[:3],
            "quiet_hours": sorted_hours[-3:],
            "total_active_hours": len(hourly_counts)
        }

    def _analyze_service_patterns(self, logs: List[Dict]) -> Dict[str, Any]:
        """Analyze service-related patterns"""
        service_stats = defaultdict(lambda: {"total": 0, "errors": 0, "avg_response_time": []})

        for log in logs:
            service = log.get("service", "unknown")
            service_stats[service]["total"] += 1

            if log.get("level") in ["ERROR", "CRITICAL"]:
                service_stats[service]["errors"] += 1

            if "response_time" in log:
                service_stats[service]["avg_response_time"].append(log["response_time"])

        # Calculate error rates and average response times
        service_summary = {}
        for service, stats in service_stats.items():
            avg_response = sum(stats["avg_response_time"]) / len(stats["avg_response_time"]) if stats[
                "avg_response_time"] else 0
            error_rate = (stats["errors"] / stats["total"]) * 100 if stats["total"] > 0 else 0

            service_summary[service] = {
                "total_requests": stats["total"],
                "error_count": stats["errors"],
                "error_rate_percent": round(error_rate, 2),
                "avg_response_time_ms": round(avg_response, 2),
                "health_score": max(0, 100 - error_rate - (avg_response / 1000 * 10))  # Simple health score
            }

        return service_summary

    def _analyze_error_patterns(self, logs: List[Dict]) -> Dict[str, Any]:
        """Analyze error patterns"""
        error_logs = [log for log in logs if log.get("level") in ["ERROR", "CRITICAL"]]

        if not error_logs:
            return {"no_errors": True}

        # Group errors by message patterns
        error_messages = [log.get("message", "") for log in error_logs]
        error_types = Counter()

        for message in error_messages:
            # Simple error categorization
            if "timeout" in message.lower():
                error_types["timeout"] += 1
            elif "connection" in message.lower():
                error_types["connection"] += 1
            elif "permission" in message.lower() or "unauthorized" in message.lower():
                error_types["authorization"] += 1
            elif "not found" in message.lower() or "404" in message:
                error_types["not_found"] += 1
            elif "internal server error" in message.lower() or "500" in message:
                error_types["server_error"] += 1
            else:
                error_types["other"] += 1

        return {
            "total_errors": len(error_logs),
            "error_types": dict(error_types),
            "error_rate_per_hour": len(error_logs) / 24,  # Assuming 24h window
            "most_common_errors": error_types.most_common(5)
        }

    def _analyze_endpoint_patterns(self, logs: List[Dict]) -> Dict[str, Any]:
        """Analyze API endpoint patterns"""
        endpoint_stats = defaultdict(lambda: {"count": 0, "response_times": [], "errors": 0})

        for log in logs:
            endpoint = log.get("endpoint")
            if endpoint:
                endpoint_stats[endpoint]["count"] += 1

                if "response_time" in log:
                    endpoint_stats[endpoint]["response_times"].append(log["response_time"])

                if log.get("level") in ["ERROR", "CRITICAL"]:
                    endpoint_stats[endpoint]["errors"] += 1

        # Calculate endpoint metrics
        endpoint_summary = {}
        for endpoint, stats in endpoint_stats.items():
            avg_response = sum(stats["response_times"]) / len(stats["response_times"]) if stats["response_times"] else 0
            error_rate = (stats["errors"] / stats["count"]) * 100 if stats["count"] > 0 else 0

            endpoint_summary[endpoint] = {
                "request_count": stats["count"],
                "avg_response_time_ms": round(avg_response, 2),
                "error_rate_percent": round(error_rate, 2),
                "requests_per_hour": stats["count"] / 24
            }

        # Find top endpoints by traffic
        top_endpoints = sorted(endpoint_summary.items(), key=lambda x: x[1]["request_count"], reverse=True)[:10]

        return {
            "total_unique_endpoints": len(endpoint_summary),
            "top_endpoints": dict(top_endpoints),
            "endpoint_summary": endpoint_summary
        }

    def _analyze_user_patterns(self, logs: List[Dict]) -> Dict[str, Any]:
        """Analyze user activity patterns"""
        user_activities = defaultdict(int)

        for log in logs:
            user_id = log.get("user_id") or log.get("client_ip")
            if user_id:
                user_activities[user_id] += 1

        if not user_activities:
            return {"no_user_data": True}

        return {
            "unique_users": len(user_activities),
            "total_user_activities": sum(user_activities.values()),
            "avg_activities_per_user": sum(user_activities.values()) / len(user_activities),
            "top_active_users": dict(Counter(user_activities).most_common(10))
        }

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
5. Risk assessment

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


# monitoring-core/app/ai/summarizer.py
import logging
from typing import List, Dict, Any
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class LogSummarizer:
    """AI-powered log summarization"""

    def __init__(self, ollama_client):
        self.ollama = ollama_client

    async def summarize_logs(self, logs: List[Dict], summary_type: str = "general") -> Dict[str, Any]:
        """Generate AI-powered log summary"""
        try:
            if not logs:
                return {"error": "No logs to summarize"}

            # Prepare logs for summarization
            log_data = self._prepare_logs_for_summary(logs, summary_type)

            # Create appropriate prompt
            prompt = self._create_summary_prompt(log_data, summary_type)

            # Get AI summary
            result = await self.ollama.generate(prompt, model="mistral")

            if result["success"]:
                summary = self._parse_summary_response(result["response"])
                summary.update({
                    "metadata": {
                        "log_count": len(logs),
                        "summary_type": summary_type,
                        "generated_at": datetime.utcnow().isoformat(),
                        "model": "mistral"
                    }
                })
                return summary
            else:
                return {"error": result.get("error"), "timestamp": datetime.utcnow().isoformat()}

        except Exception as e:
            logger.error(f"Log summarization error: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}

    def _prepare_logs_for_summary(self, logs: List[Dict], summary_type: str) -> Dict[str, Any]:
        """Prepare log data based on summary type"""
        if summary_type == "error_focus":
            # Focus on errors and warnings
            filtered_logs = [log for log in logs if log.get("level") in ["ERROR", "CRITICAL", "WARNING"]]
        elif summary_type == "performance":
            # Focus on performance metrics
            filtered_logs = [log for log in logs if
                             "response_time" in log or "performance" in log.get("message", "").lower()]
        elif summary_type == "security":
            # Focus on security-related logs
            filtered_logs = [log for log in logs if any(keyword in log.get("message", "").lower()
                                                        for keyword in
                                                        ["auth", "login", "unauthorized", "forbidden", "security",
                                                         "attack"])]
        else:
            # General summary - sample from all logs
            filtered_logs = logs[:100] if len(logs) > 100 else logs

        return {
            "original_count": len(logs),
            "filtered_count": len(filtered_logs),
            "logs": filtered_logs[:50],  # Limit to 50 logs for AI processing
            "summary_type": summary_type
        }

    def _create_summary_prompt(self, log_data: Dict, summary_type: str) -> str:
        """Create prompt for log summarization"""
        logs_text = "\n".join([
            f"[{log.get('timestamp', 'N/A')}] {log.get('level', 'INFO')} - {log.get('service', 'unknown')}: {log.get('message', '')[:200]}"
            for log in log_data["logs"]
        ])

        base_prompt = f"""
Analyze and summarize the following system logs ({summary_type} focus):

LOG DATA:
- Original log count: {log_data['original_count']}
- Filtered for analysis: {log_data['filtered_count']}
- Summary type: {summary_type}

LOGS:
{logs_text}

"""

        if summary_type == "error_focus":
            base_prompt += """
Focus on:
1. Critical errors and their frequency
2. Error patterns and root causes
3. Affected services and components
4. Recovery actions needed
5. Prevention recommendations

Provide JSON response with: critical_errors, error_patterns, affected_services, recommendations
"""
        elif summary_type == "performance":
            base_prompt += """
Focus on:
1. Performance bottlenecks
2. Response time trends
3. Resource utilization issues
4. Optimization opportunities
5. Performance recommendations

Provide JSON response with: bottlenecks, trends, issues, optimizations, recommendations
"""
        elif summary_type == "security":
            base_prompt += """
Focus on:
1. Security incidents and threats
2. Authentication/authorization issues
3. Suspicious activities
4. Security vulnerabilities
5. Security recommendations

Provide JSON response with: incidents, auth_issues, suspicious_activities, vulnerabilities, recommendations
"""
        else:
            base_prompt += """
Provide a comprehensive summary including:
1. Overall system health
2. Key events and activities
3. Notable patterns or trends
4. Issues that need attention
5. General recommendations

Provide JSON response with: health_status, key_events, patterns, issues, recommendations
"""

        return base_prompt

    def _parse_summary_response(self, ai_response: str) -> Dict[str, Any]:
        """Parse AI summary response"""
        try:
            start_idx = ai_response.find('{')
            end_idx = ai_response.rfind('}') + 1

            if start_idx >= 0 and end_idx > start_idx:
                json_str = ai_response[start_idx:end_idx]
                return json.loads(json_str)
            else:
                # Fallback to raw text summary
                return {
                    "summary": ai_response,
                    "format": "text"
                }

        except json.JSONDecodeError:
            return {
                "summary": ai_response,
                "format": "text",
                "parse_error": "Could not parse as JSON"
            }