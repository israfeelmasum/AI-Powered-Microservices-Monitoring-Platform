# monitoring-core/app/ai/anomaly_detector.py
import json
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict

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
            # Analyze historical trends
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
                return self._fallback_anomaly_detection(logs)

        except Exception as e:
            logger.error(f"Anomaly detection error: {e}")
            return self._fallback_anomaly_detection(logs)

    def _prepare_log_summary(self, logs: List[Dict]) -> Dict:
        """Prepare a summary of logs for AI analysis"""
        summary = {
            "total_logs": len(logs),
            "time_range": {
                "start": min(log.get("timestamp", "") for log in logs if log.get("timestamp")),
                "end": max(log.get("timestamp", "") for log in logs if log.get("timestamp"))
            },
            "log_levels": {},
            "services": {},
            "error_patterns": [],
            "response_times": [],
            "endpoints": {},
            "status_codes": {}
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
                    "timestamp": log.get("timestamp"),
                    "error_type": log.get("error_type", "unknown")
                })

            # Collect response times
            if "response_time" in log and log["response_time"] is not None:
                summary["response_times"].append(log["response_time"])

            # Count endpoints
            if "endpoint" in log:
                endpoint = log["endpoint"]
                summary["endpoints"][endpoint] = summary["endpoints"].get(endpoint, 0) + 1

            # Count status codes
            if "status_code" in log:
                status_code = log["status_code"]
                summary["status_codes"][str(status_code)] = summary["status_codes"].get(str(status_code), 0) + 1

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
- Response times: Average: {np.mean(log_summary['response_times']) if log_summary['response_times'] else 0:.2f}ms
- Top endpoints: {json.dumps(dict(list(log_summary['endpoints'].items())[:10]), indent=2)}
- Status codes: {json.dumps(log_summary['status_codes'], indent=2)}

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
                for i, anomaly_data in enumerate(parsed_response.get("anomalies", [])):
                    anomaly = {
                        "id": f"anomaly_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{i}",
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": anomaly_data.get("type", "unknown"),
                        "severity": anomaly_data.get("severity", "medium"),
                        "description": anomaly_data.get("description", ""),
                        "affected_services": anomaly_data.get("affected_services", []),
                        "recommendation": anomaly_data.get("recommendation", ""),
                        "detected_by": "ollama_ai",
                        "model": "mistral",
                        "log_count": len(original_logs),
                        "confidence": 0.8  # Default confidence for AI detection
                    }
                    anomalies.append(anomaly)

                return anomalies
            else:
                logger.warning("Could not extract JSON from AI response")
                return self._fallback_anomaly_detection(original_logs)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            return self._fallback_anomaly_detection(original_logs)
        except Exception as e:
            logger.error(f"Error parsing anomaly response: {e}")
            return []

    def _fallback_anomaly_detection(self, logs: List[Dict]) -> List[Dict]:
        """Fallback anomaly detection using simple heuristics"""
        anomalies = []

        # Count errors
        error_count = sum(1 for log in logs if log.get("level") in ["ERROR", "CRITICAL"])
        total_logs = len(logs)

        if error_count > total_logs * 0.1:  # More than 10% errors
            anomalies.append({
                "id": f"fallback_error_spike_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                "timestamp": datetime.utcnow().isoformat(),
                "type": "error_spike",
                "severity": "high" if error_count > total_logs * 0.2 else "medium",
                "description": f"High error rate detected: {error_count} errors in {total_logs} logs ({error_count / total_logs * 100:.1f}%)",
                "affected_services": list(
                    set(log.get("service", "unknown") for log in logs if log.get("level") in ["ERROR", "CRITICAL"])),
                "recommendation": "Investigate error causes and implement fixes",
                "detected_by": "fallback_heuristic",
                "model": "rule_based",
                "log_count": total_logs,
                "confidence": 0.7
            })

        # Check for slow response times
        response_times = [log.get("response_time") for log in logs if log.get("response_time") is not None]
        if response_times:
            avg_response_time = np.mean(response_times)
            p95_response_time = np.percentile(response_times, 95)

            if avg_response_time > 2000:  # Average response time > 2 seconds
                anomalies.append({
                    "id": f"fallback_slow_response_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "performance_issue",
                    "severity": "high" if avg_response_time > 5000 else "medium",
                    "description": f"Slow response times detected: average {avg_response_time:.0f}ms, P95 {p95_response_time:.0f}ms",
                    "affected_services": list(
                        set(log.get("service", "unknown") for log in logs if log.get("response_time", 0) > 2000)),
                    "recommendation": "Optimize slow endpoints and database queries",
                    "detected_by": "fallback_heuristic",
                    "model": "rule_based",
                    "log_count": len(response_times),
                    "confidence": 0.8
                })

        # Check for unusual status code patterns
        status_codes = [log.get("status_code") for log in logs if log.get("status_code") is not None]
        if status_codes:
            error_status_count = sum(1 for code in status_codes if code >= 500)

            if error_status_count > len(status_codes) * 0.05:  # More than 5% 5xx errors
                anomalies.append({
                    "id": f"fallback_server_errors_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "service_issue",
                    "severity": "high",
                    "description": f"High server error rate: {error_status_count} 5xx errors in {len(status_codes)} requests ({error_status_count / len(status_codes) * 100:.1f}%)",
                    "affected_services": list(
                        set(log.get("service", "unknown") for log in logs if log.get("status_code", 0) >= 500)),
                    "recommendation": "Check server health and investigate 5xx errors",
                    "detected_by": "fallback_heuristic",
                    "model": "rule_based",
                    "log_count": len(status_codes),
                    "confidence": 0.9
                })

        return anomalies