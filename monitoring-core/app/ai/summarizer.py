# monitoring-core/app/ai/summarizer.py
"""Log summarization for monitoring system"""

from typing import List, Dict, Any
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class LogSummarizer:
    """Summarizes log data for reporting and analysis"""

    def __init__(self):
        self.summary_cache = {}

    def generate_summary(self, log_entries: List[Dict[str, Any]],
                         time_period: str = '1h') -> Dict[str, Any]:
        """
        Generate a comprehensive summary of log entries

        Args:
            log_entries: List of log entries to summarize
            time_period: Time period for the summary (1h, 24h, 7d)

        Returns:
            Dictionary containing the summary
        """
        if not log_entries:
            return self._empty_summary()

        summary = {
            'period': time_period,
            'total_entries': len(log_entries),
            'time_range': self._get_time_range(log_entries),
            'log_levels': self._summarize_log_levels(log_entries),
            'sources': self._summarize_sources(log_entries),
            'top_errors': self._get_top_errors(log_entries),
            'activity_timeline': self._create_activity_timeline(log_entries),
            'health_indicators': self._calculate_health_indicators(log_entries),
            'recommendations': self._generate_recommendations(log_entries)
        }

        return summary

    def generate_metric_summary(self, metric_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate summary for metric data

        Args:
            metric_data: List of metric entries

        Returns:
            Dictionary containing metric summary
        """
        if not metric_data:
            return {'total_metrics': 0, 'message': 'No metric data available'}

        summary = {
            'total_metrics': len(metric_data),
            'time_range': self._get_time_range(metric_data),
            'metric_types': self._summarize_metric_types(metric_data),
            'statistics': self._calculate_metric_statistics(metric_data),
            'trends': self._summarize_trends(metric_data)
        }

        return summary

    def generate_executive_summary(self, log_entries: List[Dict[str, Any]],
                                   metric_data: List[Dict[str, Any]] = None,
                                   anomalies: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate high-level executive summary

        Args:
            log_entries: List of log entries
            metric_data: Optional list of metric data
            anomalies: Optional list of detected anomalies

        Returns:
            Executive summary dictionary
        """
        log_summary = self.generate_summary(log_entries)

        # Calculate overall health score
        health_score = self._calculate_overall_health(log_entries, metric_data, anomalies)

        # Identify key issues
        key_issues = self._identify_key_issues(log_entries, anomalies)

        # Generate recommendations
        recommendations = self._generate_executive_recommendations(key_issues, health_score)

        executive_summary = {
            'health_score': health_score,
            'status': self._determine_system_status(health_score),
            'key_metrics': {
                'total_logs': len(log_entries),
                'error_rate': log_summary['log_levels'].get('ERROR', 0) / max(len(log_entries), 1),
                'critical_issues': len([a for a in (anomalies or []) if a.get('severity') == 'critical']),
                'affected_services': len(log_summary['sources'])
            },
            'key_issues': key_issues,
            'recommendations': recommendations,
            'period': log_summary['time_range']
        }

        return executive_summary

    def _empty_summary(self) -> Dict[str, Any]:
        """Return empty summary structure"""
        return {
            'total_entries': 0,
            'message': 'No log entries available for summary'
        }

    def _get_time_range(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get time range of entries"""
        timestamps = []
        for entry in entries:
            timestamp = entry.get('timestamp')
            if timestamp:
                if isinstance(timestamp, str):
                    try:
                        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        timestamps.append(timestamp)
                    except:
                        continue
                elif isinstance(timestamp, datetime):
                    timestamps.append(timestamp)

        if not timestamps:
            return {'start': None, 'end': None, 'duration': None}

        start_time = min(timestamps)
        end_time = max(timestamps)
        duration = end_time - start_time

        return {
            'start': start_time.isoformat(),
            'end': end_time.isoformat(),
            'duration': str(duration)
        }

    def _summarize_log_levels(self, log_entries: List[Dict[str, Any]]) -> Dict[str, int]:
        """Summarize log entries by level"""
        level_counts = Counter()
        for entry in log_entries:
            level = entry.get('level', 'INFO')
            level_counts[level] += 1
        return dict(level_counts)

    def _summarize_sources(self, log_entries: List[Dict[str, Any]]) -> Dict[str, int]:
        """Summarize log entries by source"""
        source_counts = Counter()
        for entry in log_entries:
            source = entry.get('source', 'unknown')
            source_counts[source] += 1
        return dict(source_counts.most_common(10))

    def _get_top_errors(self, log_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get top error messages"""
        error_entries = [e for e in log_entries if e.get('level') in ['ERROR', 'CRITICAL']]

        error_messages = Counter()
        error_details = {}

        for entry in error_entries:
            message = entry.get('message', '')[:100]  # Truncate long messages
            error_messages[message] += 1
            if message not in error_details:
                error_details[message] = {
                    'first_seen': entry.get('timestamp'),
                    'source': entry.get('source', 'unknown'),
                    'level': entry.get('level', 'ERROR')
                }

        top_errors = []
        for message, count in error_messages.most_common(5):
            top_errors.append({
                'message': message,
                'count': count,
                'details': error_details[message]
            })

        return top_errors

    def _create_activity_timeline(self, log_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create activity timeline"""
        # Group entries by hour
        hourly_activity = defaultdict(lambda: {'total': 0, 'errors': 0, 'warnings': 0})

        for entry in log_entries:
            timestamp = entry.get('timestamp')
            if timestamp:
                try:
                    if isinstance(timestamp, str):
                        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

                    hour_key = timestamp.strftime('%Y-%m-%d %H:00')
                    level = entry.get('level', 'INFO')

                    hourly_activity[hour_key]['total'] += 1
                    if level == 'ERROR':
                        hourly_activity[hour_key]['errors'] += 1
                    elif level == 'WARNING':
                        hourly_activity[hour_key]['warnings'] += 1

                except:
                    continue

        # Convert to sorted list
        timeline = []
        for hour, activity in sorted(hourly_activity.items()):
            timeline.append({
                'hour': hour,
                'activity': activity
            })

        return timeline[-24:]  # Last 24 hours

    def _calculate_health_indicators(self, log_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate system health indicators"""
        total_entries = len(log_entries)
        if total_entries == 0:
            return {'score': 100, 'status': 'healthy'}

        error_count = len([e for e in log_entries if e.get('level') == 'ERROR'])
        critical_count = len([e for e in log_entries if e.get('level') == 'CRITICAL'])
        warning_count = len([e for e in log_entries if e.get('level') == 'WARNING'])

        # Calculate health score (0-100)
        error_rate = error_count / total_entries
        critical_rate = critical_count / total_entries
        warning_rate = warning_count / total_entries

        # Weighted scoring
        health_score = 100 - (critical_rate * 50 + error_rate * 30 + warning_rate * 10)
        health_score = max(0, min(100, health_score))  # Clamp to 0-100

        status = 'healthy' if health_score > 80 else 'warning' if health_score > 50 else 'critical'

        return {
            'score': round(health_score, 1),
            'status': status,
            'error_rate': round(error_rate * 100, 2),
            'critical_rate': round(critical_rate * 100, 2),
            'warning_rate': round(warning_rate * 100, 2)
        }

    def _generate_recommendations(self, log_entries: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on log analysis"""
        recommendations = []

        # Analyze error patterns
        error_count = len([e for e in log_entries if e.get('level') == 'ERROR'])
        critical_count = len([e for e in log_entries if e.get('level') == 'CRITICAL'])

        if critical_count > 0:
            recommendations.append(f"Investigate {critical_count} critical errors immediately")

        if error_count > len(log_entries) * 0.1:  # More than 10% errors
            recommendations.append("High error rate detected - review application stability")

        # Check for source diversity
        sources = set(e.get('source', 'unknown') for e in log_entries)
        if len(sources) == 1:
            recommendations.append("Consider implementing logging across more system components")

        return recommendations

    def _summarize_metric_types(self, metric_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """Summarize metrics by type"""
        type_counts = Counter()
        for entry in metric_data:
            metric_type = entry.get('metric_type', 'unknown')
            type_counts[metric_type] += 1
        return dict(type_counts)

    def _calculate_metric_statistics(self, metric_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate basic statistics for metrics"""
        values = [entry.get('value', 0) for entry in metric_data if entry.get('value') is not None]

        if not values:
            return {}

        return {
            'min': min(values),
            'max': max(values),
            'average': sum(values) / len(values),
            'count': len(values)
        }

    def _summarize_trends(self, metric_data: List[Dict[str, Any]]) -> Dict[str, str]:
        """Summarize metric trends"""
        if len(metric_data) < 2:
            return {'trend': 'insufficient_data'}

        values = [entry.get('value', 0) for entry in metric_data]
        first_half_avg = sum(values[:len(values) // 2]) / (len(values) // 2)
        second_half_avg = sum(values[len(values) // 2:]) / (len(values) - len(values) // 2)

        if second_half_avg > first_half_avg * 1.1:
            trend = 'increasing'
        elif second_half_avg < first_half_avg * 0.9:
            trend = 'decreasing'
        else:
            trend = 'stable'

        return {'trend': trend}

    def _calculate_overall_health(self, log_entries: List[Dict[str, Any]],
                                  metric_data: List[Dict[str, Any]] = None,
                                  anomalies: List[Dict[str, Any]] = None) -> float:
        """Calculate overall system health score"""
        log_health = self._calculate_health_indicators(log_entries)['score']

        # Factor in anomalies
        anomaly_penalty = 0
        if anomalies:
            critical_anomalies = len([a for a in anomalies if a.get('severity') == 'critical'])
            high_anomalies = len([a for a in anomalies if a.get('severity') == 'high'])
            anomaly_penalty = critical_anomalies * 20 + high_anomalies * 10

        overall_health = max(0, log_health - anomaly_penalty)
        return round(overall_health, 1)

    def _determine_system_status(self, health_score: float) -> str:
        """Determine system status based on health score"""
        if health_score >= 90:
            return 'excellent'
        elif health_score >= 80:
            return 'good'
        elif health_score >= 60:
            return 'warning'
        elif health_score >= 40:
            return 'poor'
        else:
            return 'critical'

    def _identify_key_issues(self, log_entries: List[Dict[str, Any]],
                             anomalies: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Identify key system issues"""
        issues = []

        # High error rate
        error_count = len([e for e in log_entries if e.get('level') == 'ERROR'])
        if error_count > len(log_entries) * 0.05:  # More than 5% errors
            issues.append({
                'type': 'high_error_rate',
                'severity': 'high',
                'description': f"Error rate is {error_count / len(log_entries) * 100:.1f}% ({error_count} errors)",
                'recommendation': 'Review application logs and fix recurring errors'
            })

        # Critical errors
        critical_count = len([e for e in log_entries if e.get('level') == 'CRITICAL'])
        if critical_count > 0:
            issues.append({
                'type': 'critical_errors',
                'severity': 'critical',
                'description': f"{critical_count} critical errors detected",
                'recommendation': 'Investigate critical errors immediately'
            })

        # Anomalies
        if anomalies:
            critical_anomalies = [a for a in anomalies if a.get('severity') == 'critical']
            if critical_anomalies:
                issues.append({
                    'type': 'critical_anomalies',
                    'severity': 'critical',
                    'description': f"{len(critical_anomalies)} critical anomalies detected",
                    'recommendation': 'Investigate anomalous behavior patterns'
                })

        return issues

    def _generate_executive_recommendations(self, key_issues: List[Dict[str, Any]],
                                            health_score: float) -> List[str]:
        """Generate executive-level recommendations"""
        recommendations = []

        if health_score < 60:
            recommendations.append("System health is concerning - immediate attention required")

        critical_issues = [i for i in key_issues if i.get('severity') == 'critical']
        if critical_issues:
            recommendations.append(f"Address {len(critical_issues)} critical issues as top priority")

        if health_score > 80:
            recommendations.append("System is performing well - maintain current monitoring practices")

        return recommendations