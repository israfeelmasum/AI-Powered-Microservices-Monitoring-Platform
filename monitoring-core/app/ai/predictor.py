# monitoring-core/app/ai/predictor.py
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
from collections import defaultdict
import numpy as np

logger = logging.getLogger(__name__)


class PredictiveInsights:
    """AI-powered predictive insights for system monitoring"""

    def __init__(self, ollama_client):
        self.ollama = ollama_client

    async def generate_predictions(self,
                                   historical_data: List[Dict],
                                   prediction_type: str = "general") -> Dict[str, Any]:
        """Generate predictive insights based on historical data"""
        try:
            if not historical_data:
                return {"error": "No historical data available for predictions"}

            # Analyze historical trends
            trends = self._analyze_trends(historical_data)

            # Generate AI-powered predictions
            ai_predictions = await self._ai_predict(trends, prediction_type)

            # Calculate confidence scores
            confidence_scores = self._calculate_confidence(trends, ai_predictions)

            return {
                "predictions": ai_predictions,
                "trends": trends,
                "confidence": confidence_scores,
                "prediction_type": prediction_type,
                "data_points": len(historical_data),
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Prediction generation error: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}

    def _analyze_trends(self, data: List[Dict]) -> Dict[str, Any]:
        """Analyze historical trends in the data"""
        trends = {
            "error_rate_trend": self._calculate_error_trend(data),
            "performance_trend": self._calculate_performance_trend(data),
            "volume_trend": self._calculate_volume_trend(data),
            "service_health_trend": self._calculate_service_health_trend(data)
        }
        return trends

    def _calculate_error_trend(self, data: List[Dict]) -> Dict[str, Any]:
        """Calculate error rate trends"""
        error_counts = []
        total_counts = []
        timestamps = []

        # Group data by time periods (e.g., hourly)
        time_buckets = defaultdict(lambda: {"errors": 0, "total": 0})

        for log in data:
            try:
                timestamp = datetime.fromisoformat(log.get("timestamp", "").replace('Z', '+00:00'))
                hour_key = timestamp.replace(minute=0, second=0, microsecond=0)

                time_buckets[hour_key]["total"] += 1
                if log.get("level") in ["ERROR", "CRITICAL"]:
                    time_buckets[hour_key]["errors"] += 1
            except:
                continue

        # Calculate error rates
        for time_key in sorted(time_buckets.keys()):
            bucket = time_buckets[time_key]
            error_rate = (bucket["errors"] / bucket["total"] * 100) if bucket["total"] > 0 else 0
            error_counts.append(error_rate)
            total_counts.append(bucket["total"])
            timestamps.append(time_key.isoformat())

        # Calculate trend direction
        if len(error_counts) >= 2:
            recent_avg = np.mean(error_counts[-3:]) if len(error_counts) >= 3 else error_counts[-1]
            older_avg = np.mean(error_counts[:-3]) if len(error_counts) > 3 else error_counts[0]
            trend_direction = "increasing" if recent_avg > older_avg else "decreasing" if recent_avg < older_avg else "stable"
        else:
            trend_direction = "insufficient_data"

        return {
            "current_rate": error_counts[-1] if error_counts else 0,
            "avg_rate": np.mean(error_counts) if error_counts else 0,
            "trend_direction": trend_direction,
            "data_points": len(error_counts),
            "timestamps": timestamps[-10:],  # Last 10 data points
            "values": error_counts[-10:]
        }

    def _calculate_performance_trend(self, data: List[Dict]) -> Dict[str, Any]:
        """Calculate performance trends"""
        response_times = []
        timestamps = []

        for log in data:
            if "response_time" in log:
                try:
                    response_times.append(log["response_time"])
                    timestamps.append(log.get("timestamp", ""))
                except:
                    continue

        if not response_times:
            return {"no_performance_data": True}

        # Calculate trend
        if len(response_times) >= 10:
            recent_avg = np.mean(response_times[-5:])
            older_avg = np.mean(response_times[:-5])
            trend_direction = "deteriorating" if recent_avg > older_avg else "improving" if recent_avg < older_avg else "stable"
        else:
            trend_direction = "insufficient_data"

        return {
            "current_avg_ms": round(
                np.mean(response_times[-5:]) if len(response_times) >= 5 else np.mean(response_times), 2),
            "overall_avg_ms": round(np.mean(response_times), 2),
            "p95_ms": round(np.percentile(response_times, 95), 2),
            "trend_direction": trend_direction,
            "data_points": len(response_times)
        }

    def _calculate_volume_trend(self, data: List[Dict]) -> Dict[str, Any]:
        """Calculate request volume trends"""
        # Group by time periods
        time_buckets = defaultdict(int)

        for log in data:
            try:
                timestamp = datetime.fromisoformat(log.get("timestamp", "").replace('Z', '+00:00'))
                hour_key = timestamp.replace(minute=0, second=0, microsecond=0)
                time_buckets[hour_key] += 1
            except:
                continue

        volumes = list(time_buckets.values())

        if len(volumes) >= 2:
            recent_avg = np.mean(volumes[-3:]) if len(volumes) >= 3 else volumes[-1]
            older_avg = np.mean(volumes[:-3]) if len(volumes) > 3 else volumes[0]
            trend_direction = "increasing" if recent_avg > older_avg else "decreasing" if recent_avg < older_avg else "stable"
        else:
            trend_direction = "insufficient_data"

        return {
            "current_volume": volumes[-1] if volumes else 0,
            "avg_volume": round(np.mean(volumes), 2) if volumes else 0,
            "peak_volume": max(volumes) if volumes else 0,
            "trend_direction": trend_direction,
            "data_points": len(volumes)
        }

    def _calculate_service_health_trend(self, data: List[Dict]) -> Dict[str, Any]:
        """Calculate service health trends"""
        service_metrics = defaultdict(lambda: {"total": 0, "errors": 0, "response_times": []})

        for log in data:
            service = log.get("service", "unknown")
            service_metrics[service]["total"] += 1

            if log.get("level") in ["ERROR", "CRITICAL"]:
                service_metrics[service]["errors"] += 1

            if "response_time" in log:
                service_metrics[service]["response_times"].append(log["response_time"])

        service_health = {}
        for service, metrics in service_metrics.items():
            error_rate = (metrics["errors"] / metrics["total"] * 100) if metrics["total"] > 0 else 0
            avg_response_time = np.mean(metrics["response_times"]) if metrics["response_times"] else 0

            # Calculate health score (0-100)
            health_score = max(0, 100 - error_rate - (avg_response_time / 1000 * 10))

            service_health[service] = {
                "health_score": round(health_score, 2),
                "error_rate": round(error_rate, 2),
                "avg_response_time": round(avg_response_time, 2),
                "total_requests": metrics["total"]
            }

        return service_health

    async def _ai_predict(self, trends: Dict[str, Any], prediction_type: str) -> Dict[str, Any]:
        """Generate AI predictions based on trends"""
        try:
            prompt = self._create_prediction_prompt(trends, prediction_type)
            result = await self.ollama.generate(prompt, model="mistral")

            if result["success"]:
                return self._parse_prediction_response(result["response"])
            else:
                return {"ai_prediction_failed": True, "error": result.get("error")}

        except Exception as e:
            logger.error(f"AI prediction error: {e}")
            return {"ai_prediction_failed": True, "error": str(e)}

    def _create_prediction_prompt(self, trends: Dict[str, Any], prediction_type: str) -> str:
        """Create prompt for AI predictions"""
        return f"""
Based on the following system trends, provide predictions and recommendations:

TRENDS ANALYSIS:
{json.dumps(trends, indent=2)}

PREDICTION TYPE: {prediction_type}

Please analyze these trends and provide:
1. Short-term predictions (next 1-4 hours)
2. Medium-term predictions (next 24 hours)
3. Potential issues to watch for
4. Recommended preventive actions
5. Confidence level in predictions

Focus on:
- System performance trends
- Error rate projections
- Resource utilization forecasts
- Service health predictions

Format response as JSON with keys: short_term, medium_term, potential_issues, recommendations, confidence_level
"""

    def _parse_prediction_response(self, ai_response: str) -> Dict[str, Any]:
        """Parse AI prediction response"""
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

    def _calculate_confidence(self, trends: Dict[str, Any], predictions: Dict[str, Any]) -> Dict[str, float]:
        """Calculate confidence scores for predictions"""
        confidence_scores = {}

        # Base confidence on data quality and trends stability
        base_confidence = 0.5

        # Adjust based on data points
        error_trend = trends.get("error_rate_trend", {})
        if error_trend.get("data_points", 0) >= 10:
            base_confidence += 0.2

        # Adjust based on trend stability
        if error_trend.get("trend_direction") != "insufficient_data":
            base_confidence += 0.1

        performance_trend = trends.get("performance_trend", {})
        if not performance_trend.get("no_performance_data", False):
            base_confidence += 0.1

        # AI prediction quality
        if not predictions.get("ai_prediction_failed", False):
            base_confidence += 0.1

        confidence_scores = {
            "overall": min(1.0, base_confidence),
            "short_term": min(1.0, base_confidence + 0.1),
            "medium_term": min(1.0, base_confidence - 0.1),
            "error_predictions": min(1.0, base_confidence + 0.05),
            "performance_predictions": min(1.0, base_confidence - 0.05)
        }

        return confidence_scores