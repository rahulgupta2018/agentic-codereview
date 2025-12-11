"""
Metrics and observability for the agentic code review system.

Provides Prometheus-style metrics for:
- Callback execution time
- Filtered findings (hallucinations, false positives, bias)
- Confidence scores
- Evaluation scores
- Quality loop iterations

Following the design in docs/CALLBACKS_GUARDRAILS_DESIGN.md
"""

import logging
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CallbackMetrics:
    """Metrics for callback execution."""
    execution_count: int = 0
    total_duration_ms: float = 0.0
    filtered_hallucinations: int = 0
    filtered_false_positives: int = 0
    filtered_bias: int = 0
    validated_cves: int = 0
    invalid_cves: int = 0
    callback_errors: int = 0
    
    def avg_duration_ms(self) -> float:
        """Calculate average callback execution time."""
        if self.execution_count == 0:
            return 0.0
        return self.total_duration_ms / self.execution_count
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for logging."""
        return {
            'execution_count': self.execution_count,
            'avg_duration_ms': round(self.avg_duration_ms(), 2),
            'total_duration_ms': round(self.total_duration_ms, 2),
            'filtered_hallucinations': self.filtered_hallucinations,
            'filtered_false_positives': self.filtered_false_positives,
            'filtered_bias': self.filtered_bias,
            'validated_cves': self.validated_cves,
            'invalid_cves': self.invalid_cves,
            'callback_errors': self.callback_errors
        }


@dataclass
class ConfidenceMetrics:
    """Metrics for confidence scoring."""
    scores: List[float] = field(default_factory=list)
    high_confidence_count: int = 0  # >= 0.90
    medium_confidence_count: int = 0  # 0.70-0.89
    low_confidence_count: int = 0  # < 0.70
    
    def add_score(self, score: float):
        """Add a confidence score."""
        self.scores.append(score)
        if score >= 0.90:
            self.high_confidence_count += 1
        elif score >= 0.70:
            self.medium_confidence_count += 1
        else:
            self.low_confidence_count += 1
    
    def avg_score(self) -> float:
        """Calculate average confidence score."""
        if not self.scores:
            return 0.0
        return sum(self.scores) / len(self.scores)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for logging."""
        return {
            'total_findings': len(self.scores),
            'avg_score': round(self.avg_score(), 2),
            'high_confidence': self.high_confidence_count,
            'medium_confidence': self.medium_confidence_count,
            'low_confidence': self.low_confidence_count
        }


@dataclass
class EvaluationMetrics:
    """Metrics for evaluator agent scoring."""
    evaluation_scores: List[float] = field(default_factory=list)
    flagged_for_review: int = 0
    auto_filtered: int = 0
    false_positive_rate: float = 0.0
    
    def add_evaluation(self, score: float, flagged: bool = False, filtered: bool = False):
        """Add an evaluation score."""
        self.evaluation_scores.append(score)
        if flagged:
            self.flagged_for_review += 1
        if filtered:
            self.auto_filtered += 1
    
    def avg_score(self) -> float:
        """Calculate average evaluation score."""
        if not self.evaluation_scores:
            return 0.0
        return sum(self.evaluation_scores) / len(self.evaluation_scores)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for logging."""
        return {
            'total_evaluations': len(self.evaluation_scores),
            'avg_score': round(self.avg_score(), 2),
            'flagged_for_review': self.flagged_for_review,
            'auto_filtered': self.auto_filtered,
            'false_positive_rate': round(self.false_positive_rate, 3)
        }


@dataclass
class QualityLoopMetrics:
    """Metrics for quality loop refinement."""
    iterations: int = 0
    duration_seconds: float = 0.0
    improvements_applied: int = 0
    exit_reason: str = ""  # approved, max_iterations, timeout, error
    initial_quality_score: float = 0.0
    final_quality_score: float = 0.0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for logging."""
        return {
            'iterations': self.iterations,
            'duration_seconds': round(self.duration_seconds, 2),
            'improvements_applied': self.improvements_applied,
            'exit_reason': self.exit_reason,
            'initial_quality_score': round(self.initial_quality_score, 2),
            'final_quality_score': round(self.final_quality_score, 2),
            'quality_improvement': round(self.final_quality_score - self.initial_quality_score, 2)
        }


class MetricsCollector:
    """Central metrics collector for the system."""
    
    def __init__(self):
        self.callback_metrics: Dict[str, CallbackMetrics] = {}
        self.confidence_metrics: Dict[str, ConfidenceMetrics] = {}
        self.evaluation_metrics: Dict[str, EvaluationMetrics] = {}
        self.quality_loop_metrics: List[QualityLoopMetrics] = []
        self.session_start_time: Optional[datetime] = None
    
    def start_session(self, session_id: str):
        """Start tracking metrics for a session."""
        self.session_start_time = datetime.now()
        logger.info(f"📊 [MetricsCollector] Started session: {session_id}")
    
    def record_callback_execution(
        self,
        agent_name: str,
        callback_type: str,
        duration_ms: float,
        filtered_items: Dict[str, int] = None
    ):
        """Record callback execution metrics."""
        key = f"{agent_name}_{callback_type}"
        
        if key not in self.callback_metrics:
            self.callback_metrics[key] = CallbackMetrics()
        
        metrics = self.callback_metrics[key]
        metrics.execution_count += 1
        metrics.total_duration_ms += duration_ms
        
        if filtered_items:
            metrics.filtered_hallucinations += filtered_items.get('hallucinations', 0)
            metrics.filtered_false_positives += filtered_items.get('false_positives', 0)
            metrics.filtered_bias += filtered_items.get('bias', 0)
            metrics.validated_cves += filtered_items.get('validated_cves', 0)
            metrics.invalid_cves += filtered_items.get('invalid_cves', 0)
        
        # Alert if callback duration exceeds threshold
        if duration_ms > 100:
            logger.warning(
                f"⚠️ [MetricsCollector] Callback exceeded budget: "
                f"{agent_name}.{callback_type} took {duration_ms:.2f}ms (threshold: 100ms)"
            )
    
    def record_callback_error(self, agent_name: str, callback_type: str):
        """Record callback error."""
        key = f"{agent_name}_{callback_type}"
        
        if key not in self.callback_metrics:
            self.callback_metrics[key] = CallbackMetrics()
        
        self.callback_metrics[key].callback_errors += 1
    
    def record_confidence_score(self, agent_name: str, score: float):
        """Record confidence score."""
        if agent_name not in self.confidence_metrics:
            self.confidence_metrics[agent_name] = ConfidenceMetrics()
        
        self.confidence_metrics[agent_name].add_score(score)
    
    def record_evaluation(
        self,
        agent_name: str,
        evaluation_score: float,
        flagged: bool = False,
        filtered: bool = False
    ):
        """Record evaluation metrics."""
        if agent_name not in self.evaluation_metrics:
            self.evaluation_metrics[agent_name] = EvaluationMetrics()
        
        self.evaluation_metrics[agent_name].add_evaluation(evaluation_score, flagged, filtered)
    
    def record_quality_loop(self, metrics: QualityLoopMetrics):
        """Record quality loop metrics."""
        self.quality_loop_metrics.append(metrics)
        
        logger.info(
            f"🔁 [MetricsCollector] Quality loop completed: "
            f"{metrics.iterations} iterations, {metrics.exit_reason}, "
            f"quality improved {metrics.final_quality_score - metrics.initial_quality_score:.2f}"
        )
    
    def get_summary(self) -> Dict:
        """Get summary of all metrics."""
        return {
            'callbacks': {
                name: metrics.to_dict()
                for name, metrics in self.callback_metrics.items()
            },
            'confidence': {
                agent: metrics.to_dict()
                for agent, metrics in self.confidence_metrics.items()
            },
            'evaluation': {
                agent: metrics.to_dict()
                for agent, metrics in self.evaluation_metrics.items()
            },
            'quality_loop': [
                metrics.to_dict()
                for metrics in self.quality_loop_metrics
            ] if self.quality_loop_metrics else None,
            'session_duration_seconds': (
                (datetime.now() - self.session_start_time).total_seconds()
                if self.session_start_time else 0
            )
        }
    
    def log_summary(self, session_id: str):
        """Log metrics summary."""
        summary = self.get_summary()
        
        logger.info("=" * 80)
        logger.info(f"📊 METRICS SUMMARY - Session: {session_id}")
        logger.info("=" * 80)
        
        # Callback metrics
        if summary['callbacks']:
            logger.info("\n🛡️ CALLBACK METRICS:")
            for callback_name, metrics in summary['callbacks'].items():
                logger.info(f"  {callback_name}:")
                logger.info(f"    Executions: {metrics['execution_count']}")
                logger.info(f"    Avg Duration: {metrics['avg_duration_ms']}ms")
                logger.info(f"    Filtered - Hallucinations: {metrics['filtered_hallucinations']}, "
                          f"False Positives: {metrics['filtered_false_positives']}, "
                          f"Bias: {metrics['filtered_bias']}")
                if metrics['callback_errors'] > 0:
                    logger.warning(f"    ⚠️ Errors: {metrics['callback_errors']}")
        
        # Confidence metrics
        if summary['confidence']:
            logger.info("\n💯 CONFIDENCE METRICS:")
            for agent, metrics in summary['confidence'].items():
                logger.info(f"  {agent}:")
                logger.info(f"    Total Findings: {metrics['total_findings']}")
                logger.info(f"    Avg Score: {metrics['avg_score']}")
                logger.info(f"    Distribution - High: {metrics['high_confidence']}, "
                          f"Medium: {metrics['medium_confidence']}, "
                          f"Low: {metrics['low_confidence']}")
        
        # Evaluation metrics
        if summary['evaluation']:
            logger.info("\n📋 EVALUATION METRICS:")
            for agent, metrics in summary['evaluation'].items():
                logger.info(f"  {agent}:")
                logger.info(f"    Total Evaluations: {metrics['total_evaluations']}")
                logger.info(f"    Avg Score: {metrics['avg_score']}")
                logger.info(f"    Flagged for Review: {metrics['flagged_for_review']}")
                logger.info(f"    Auto-Filtered: {metrics['auto_filtered']}")
        
        # Quality loop metrics
        if summary['quality_loop']:
            logger.info("\n🔁 QUALITY LOOP METRICS:")
            for metrics in summary['quality_loop']:
                logger.info(f"  Iterations: {metrics['iterations']}, "
                          f"Duration: {metrics['duration_seconds']}s, "
                          f"Exit: {metrics['exit_reason']}")
                logger.info(f"  Quality: {metrics['initial_quality_score']} → {metrics['final_quality_score']} "
                          f"(+{metrics['quality_improvement']})")
        
        logger.info(f"\n⏱️  Total Session Duration: {summary['session_duration_seconds']:.2f}s")
        logger.info("=" * 80)
    
    def reset(self):
        """Reset all metrics."""
        self.callback_metrics.clear()
        self.confidence_metrics.clear()
        self.evaluation_metrics.clear()
        self.quality_loop_metrics.clear()
        self.session_start_time = None


# Global metrics collector instance
_metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    return _metrics_collector


# Convenience function for timing callbacks
class CallbackTimer:
    """Context manager for timing callback execution."""
    
    def __init__(self, agent_name: str, callback_type: str, metrics_collector: MetricsCollector = None):
        self.agent_name = agent_name
        self.callback_type = callback_type
        self.metrics_collector = metrics_collector or get_metrics_collector()
        self.start_time = None
        self.filtered_items = {}
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        
        if exc_type is not None:
            # Error occurred
            self.metrics_collector.record_callback_error(self.agent_name, self.callback_type)
        else:
            # Successful execution
            self.metrics_collector.record_callback_execution(
                self.agent_name,
                self.callback_type,
                duration_ms,
                self.filtered_items
            )
    
    def record_filtered(self, category: str, count: int):
        """Record filtered items during callback execution."""
        self.filtered_items[category] = self.filtered_items.get(category, 0) + count


logger.info("✅ [metrics.py] Metrics collection system loaded")
