"""
Lightweight telemetry/observability helper.
Falls back to structured logging when Prometheus client is unavailable.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional, Tuple

try:
    from prometheus_client import Counter, Gauge, Histogram  # type: ignore

    PROM_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    PROM_AVAILABLE = False


class TelemetryClient:
    """Simple telemetry helper supporting increment/gauge/observe."""

    def __init__(self, config: Dict[str, any]):
        self.logger = logging.getLogger(__name__)
        self.enabled = config.get('enable_telemetry', True)
        self.exporter = config.get('telemetry_exporter', 'prometheus')
        self._counters: Dict[Tuple[str, Tuple[str, ...]], Counter] = {}
        self._gauges: Dict[Tuple[str, Tuple[str, ...]], Gauge] = {}
        self._histograms: Dict[Tuple[str, Tuple[str, ...]], Histogram] = {}

    def _should_use_prometheus(self) -> bool:
        return self.enabled and self.exporter == 'prometheus' and PROM_AVAILABLE

    def increment(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        if not self.enabled:
            return
        labels = labels or {}
        if self._should_use_prometheus():
            counter = self._get_counter(name, labels)
            counter.labels(**labels).inc(value)
        else:
            self.logger.info("metric_increment", extra={'metric': name, 'value': value, 'labels': labels})

    def gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        if not self.enabled:
            return
        labels = labels or {}
        if self._should_use_prometheus():
            gauge = self._get_gauge(name, labels)
            gauge.labels(**labels).set(value)
        else:
            self.logger.info("metric_gauge", extra={'metric': name, 'value': value, 'labels': labels})

    def observe(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        if not self.enabled:
            return
        labels = labels or {}
        if self._should_use_prometheus():
            histogram = self._get_histogram(name, labels)
            histogram.labels(**labels).observe(value)
        else:
            self.logger.info("metric_observe", extra={'metric': name, 'value': value, 'labels': labels})

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _metric_key(self, name: str, labels: Dict[str, str]) -> Tuple[str, Tuple[str, ...]]:
        return name, tuple(sorted(labels.keys()))

    def _get_counter(self, name: str, labels: Dict[str, str]) -> Counter:
        key = self._metric_key(name, labels)
        if key not in self._counters:
            self._counters[key] = Counter(name, f"{name} counter", labelnames=list(labels.keys()))
        return self._counters[key]

    def _get_gauge(self, name: str, labels: Dict[str, str]) -> Gauge:
        key = self._metric_key(name, labels)
        if key not in self._gauges:
            self._gauges[key] = Gauge(name, f"{name} gauge", labelnames=list(labels.keys()))
        return self._gauges[key]

    def _get_histogram(self, name: str, labels: Dict[str, str]) -> Histogram:
        key = self._metric_key(name, labels)
        if key not in self._histograms:
            self._histograms[key] = Histogram(name, f"{name} histogram", labelnames=list(labels.keys()))
        return self._histograms[key]
    
    # ------------------------------------------------------------------ #
    # Enhanced metrics for comprehensive observability (#21)
    # ------------------------------------------------------------------ #
    
    def record_model_metrics(self, model_version: int, train_auc: float, test_auc: float,
                            train_accuracy: float, test_accuracy: float, brier_score: float) -> None:
        """
        Record model training metrics over time (#21)
        
        Args:
            model_version: Model version number
            train_auc: Training AUC
            test_auc: Test AUC
            train_accuracy: Training accuracy
            test_accuracy: Test accuracy
            brier_score: Brier score
        """
        labels = {'model_version': str(model_version)}
        
        self.gauge('model_train_auc', train_auc, labels)
        self.gauge('model_test_auc', test_auc, labels)
        self.gauge('model_train_accuracy', train_accuracy, labels)
        self.gauge('model_test_accuracy', test_accuracy, labels)
        self.gauge('model_brier_score', brier_score, labels)
    
    def record_bid_change_magnitude(self, entity_type: str, adjustment_percentage: float) -> None:
        """
        Record bid change magnitude for analysis (#21)
        
        Args:
            entity_type: Type of entity
            adjustment_percentage: Adjustment percentage
        """
        self.observe(
            'bid_change_magnitude',
            abs(adjustment_percentage),
            labels={'entity_type': entity_type}
        )
    
    def record_learning_metrics(self, success_rate: float, total_outcomes: int,
                               avg_improvement: float) -> None:
        """
        Record learning loop metrics (#21)
        
        Args:
            success_rate: Success rate (0-1)
            total_outcomes: Total number of outcomes
            avg_improvement: Average improvement percentage
        """
        self.gauge('learning_success_rate', success_rate)
        self.gauge('learning_total_outcomes', float(total_outcomes))
        self.gauge('learning_avg_improvement', avg_improvement)


