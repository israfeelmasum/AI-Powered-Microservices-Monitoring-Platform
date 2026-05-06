# monitoring-core/app/storage/elasticsearch_index_config.py

INDICES_CONFIG = {
    "monitoring-logs": {
        "mappings": {
            "properties": {
                "timestamp": {"type": "date"},
                "service": {"type": "keyword"},
                "level": {"type": "keyword"},
                "message": {"type": "text", "analyzer": "standard"},
                "correlation_id": {"type": "keyword"},
                "endpoint": {"type": "keyword"},
                "method": {"type": "keyword"},
                "path": {"type": "keyword"},
                "status_code": {"type": "integer"},
                "response_time": {"type": "float"},
                "client_ip": {"type": "ip"},
                "user_agent": {"type": "text"},
                "error_type": {"type": "keyword"},
                "error_message": {"type": "text"},
                "exception_type": {"type": "keyword"},
                "system_metrics": {
                    "properties": {
                        "cpu_percent": {"type": "float"},
                        "memory_mb": {"type": "float"},
                        "memory_percent": {"type": "float"},
                        "memory_change_mb": {"type": "float"},
                        "num_threads": {"type": "integer"},
                        "open_files": {"type": "integer"},
                        "connections": {"type": "integer"}
                    }
                },
                "query_params": {"type": "object", "enabled": False},
                "request_size": {"type": "integer"},
                "response_size": {"type": "integer"}
            }
        },
        "settings": {
            "index": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "refresh_interval": "5s",
                "max_result_window": 50000
            },
            "analysis": {
                "analyzer": {
                    "log_analyzer": {
                        "type": "standard",
                        "stopwords": "_none_"
                    }
                }
            }
        }
    },
    "monitoring-metrics": {
        "mappings": {
            "properties": {
                "timestamp": {"type": "date"},
                "service": {"type": "keyword"},
                "metric_name": {"type": "keyword"},
                "metric_value": {"type": "float"},
                "metric_type": {"type": "keyword"},
                "tags": {"type": "object", "dynamic": True},
                "metrics": {"type": "object", "dynamic": True},
                "counters": {"type": "object", "dynamic": True},
                "gauges": {"type": "object", "dynamic": True},
                "histograms": {"type": "object", "dynamic": True}
            }
        },
        "settings": {
            "index": {
                "number_of_shards": 1,
                "number_of_replicas": 0
            }
        }
    },
    "monitoring-anomalies": {
        "mappings": {
            "properties": {
                "timestamp": {"type": "date"},
                "service": {"type": "keyword"},
                "anomaly_id": {"type": "keyword"},
                "type": {"type": "keyword"},
                "severity": {"type": "keyword"},
                "description": {"type": "text"},
                "recommendation": {"type": "text"},
                "detected_by": {"type": "keyword"},
                "model": {"type": "keyword"},
                "confidence": {"type": "float"},
                "affected_services": {"type": "keyword"},
                "log_count": {"type": "integer"},
                "error_rate": {"type": "float"},
                "response_time": {"type": "float"}
            }
        }
    },
    "monitoring-health": {
        "mappings": {
            "properties": {
                "timestamp": {"type": "date"},
                "service": {"type": "keyword"},
                "status": {"type": "keyword"},
                "health_score": {"type": "float"},
                "checks": {"type": "object", "dynamic": True},
                "system_metrics": {"type": "object", "dynamic": True},
                "uptime": {"type": "long"},
                "last_error": {"type": "text"},
                "error_count": {"type": "integer"}
            }
        }
    },
    "monitoring-services": {
        "mappings": {
            "properties": {
                "service_name": {"type": "keyword"},
                "service_url": {"type": "keyword"},
                "version": {"type": "keyword"},
                "registered_at": {"type": "date"},
                "last_seen": {"type": "date"},
                "status": {"type": "keyword"},
                "endpoints": {"type": "object", "dynamic": True},
                "capabilities": {"type": "keyword"},
                "health_check_url": {"type": "keyword"},
                "metadata": {"type": "object", "dynamic": True}
            }
        }
    }
}
