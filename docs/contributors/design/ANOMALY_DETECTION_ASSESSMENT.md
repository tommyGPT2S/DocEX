# Anomaly Detection Assessment: DocEX Built-in vs NixtlaClient

## Executive Summary

**For Anomaly Detection: NixtlaClient could be valuable, but only if you need statistical/pattern-based detection beyond simple thresholds.**

DocEX currently has **threshold-based anomaly detection** which works well for most cases. NixtlaClient provides **statistical anomaly detection** which is better for detecting subtle patterns, trends, and anomalies that thresholds might miss.

---

## Current DocEX Anomaly Detection

### ✅ Threshold-Based Detection (Current)

DocEX uses simple threshold-based detection:

```python
# From VectorDatabaseMonitor
threshold = self.thresholds['query_latency_ms']  # e.g., 1000ms
status = (
    HealthStatus.HEALTHY if latency < threshold else 
    HealthStatus.DEGRADED if latency < threshold * 2 else 
    HealthStatus.UNHEALTHY
)
```

**What it detects:**
- ✅ Values exceeding fixed thresholds
- ✅ Clear performance degradation
- ✅ Error rate spikes
- ✅ Memory usage spikes

**Limitations:**
- ❌ Can't detect subtle anomalies (e.g., 5% slower than normal)
- ❌ Can't detect gradual degradation over time
- ❌ Can't detect seasonal patterns
- ❌ Can't detect anomalies in trends (e.g., "unusually slow for this time of day")
- ❌ Requires manual threshold tuning
- ❌ False positives when thresholds are too sensitive

**Example:**
```python
# Current: Detects if latency > 1000ms
if latency > 1000:
    alert("High latency detected")

# Problem: What if normal latency is 800ms, and it spikes to 950ms?
# This is a 19% increase but won't trigger alert
```

---

## NixtlaClient Anomaly Detection

### ✅ Statistical/Pattern-Based Detection

NixtlaClient provides advanced anomaly detection using statistical models:

```python
from nixtla import NixtlaClient

client = NixtlaClient(api_key="...")

# Detect anomalies in time series data
anomalies = client.detect_anomalies(
    y=operation_latencies,  # Historical latency data
    freq="H",  # Hourly data
    model="auto_arima"
)

# Returns:
# - Anomaly scores for each point
# - Statistical confidence levels
# - Pattern-based detection (seasonality, trends)
```

**What it detects:**
- ✅ Subtle anomalies (statistical outliers)
- ✅ Gradual degradation over time
- ✅ Seasonal patterns (e.g., "unusually slow for Monday mornings")
- ✅ Trend anomalies (e.g., "latency increasing faster than normal")
- ✅ Context-aware detection (compares to historical patterns)
- ✅ Statistical confidence scores

**Advantages:**
- ✅ No manual threshold tuning needed
- ✅ Adapts to changing baselines
- ✅ Detects anomalies relative to historical patterns
- ✅ Can detect multiple types of anomalies (spikes, dips, trends)

**Example:**
```python
# NixtlaClient: Detects if latency is statistically unusual
# Even if it's within threshold, it can detect:
# - "This is unusually slow for 2pm on a Tuesday"
# - "Latency has been gradually increasing over the past week"
# - "This spike is 3 standard deviations from normal"
```

---

## Comparison: Threshold vs Statistical Detection

| Scenario | Threshold-Based (DocEX) | Statistical (NixtlaClient) |
|----------|-------------------------|----------------------------|
| **Latency spikes > 1000ms** | ✅ Detects | ✅ Detects |
| **Gradual 20% increase over week** | ❌ Misses | ✅ Detects |
| **Unusually slow for time of day** | ❌ Misses | ✅ Detects |
| **Seasonal patterns** | ❌ Misses | ✅ Detects |
| **5% performance degradation** | ❌ Misses (if below threshold) | ✅ Detects |
| **False positives** | ⚠️ High (if threshold too low) | ✅ Lower (statistical confidence) |
| **Setup complexity** | ✅ Low | ⚠️ Medium |
| **Real-time detection** | ✅ Yes | ⚠️ Requires historical data |
| **Adaptive to changes** | ❌ No (manual tuning) | ✅ Yes (learns patterns) |

---

## When to Use Each Approach

### Use DocEX Threshold-Based Detection When:

1. **Simple, clear-cut anomalies** ✅
   - "Error rate > 5%"
   - "Latency > 1000ms"
   - "Memory > 1GB"

2. **Real-time monitoring** ✅
   - Immediate alerts needed
   - No historical data required
   - Simple to understand

3. **Known performance baselines** ✅
   - Clear thresholds (e.g., SLA targets)
   - Predictable workloads
   - Static environments

4. **Low complexity requirements** ✅
   - Minimal setup
   - No statistical expertise needed
   - Quick implementation

### Use NixtlaClient Statistical Detection When:

1. **Subtle anomaly detection** ✅
   - Need to detect gradual degradation
   - Want to catch issues before they become critical
   - Need context-aware detection

2. **Pattern-based anomalies** ✅
   - Detect anomalies relative to historical patterns
   - Seasonal pattern detection
   - Trend anomaly detection

3. **Adaptive detection** ✅
   - Baselines change over time
   - Workloads are variable
   - Need automatic threshold adjustment

4. **Advanced analytics** ✅
   - Statistical confidence scores
   - Multiple anomaly types
   - Predictive anomaly detection

---

## Hybrid Approach: Best of Both Worlds

### Recommended: Enhance DocEX with Statistical Detection

You can add statistical anomaly detection to DocEX without replacing threshold-based detection:

```python
from docex.processors.rag.vector_db_monitor import VectorDatabaseMonitor
from docex.services.anomaly_detection_service import AnomalyDetectionService

# Keep threshold-based for critical alerts
monitor = VectorDatabaseMonitor(vector_db, config={
    'query_latency_threshold': 1000,  # Critical threshold
    'error_rate_threshold': 5,
})

# Add statistical detection for subtle anomalies
anomaly_service = AnomalyDetectionService(
    model='nixtla',  # or 'simple_stats', 'isolation_forest', etc.
    config={
        'sensitivity': 'medium',  # low, medium, high
        'min_history_days': 7,  # Need 7 days of data
        'detection_window': '24h',  # Check last 24 hours
    }
)

# Run both
report = await monitor.health_check()

# Add statistical anomaly detection
if anomaly_service.has_sufficient_history():
    anomalies = await anomaly_service.detect_anomalies(
        metric='query_latency',
        time_window='24h'
    )
    
    # Combine results
    for anomaly in anomalies:
        if anomaly.confidence > 0.8:  # High confidence
            report.warnings.append(
                f"Statistical anomaly detected: {anomaly.description}"
            )
```

---

## Implementation Options

### Option 1: Simple Statistical Detection (No NixtlaClient)

Add basic statistical detection using Python libraries:

```python
import numpy as np
from scipy import stats

class SimpleAnomalyDetector:
    """Simple statistical anomaly detector"""
    
    def detect_anomalies(self, values: List[float], window: int = 100):
        """Detect anomalies using Z-score"""
        if len(values) < window:
            return []  # Need enough history
        
        recent = values[-window:]
        mean = np.mean(recent)
        std = np.std(recent)
        
        anomalies = []
        for i, value in enumerate(recent[-24:]):  # Check last 24 points
            z_score = abs((value - mean) / std) if std > 0 else 0
            
            if z_score > 2:  # 2 standard deviations
                anomalies.append({
                    'index': len(values) - 24 + i,
                    'value': value,
                    'z_score': z_score,
                    'severity': 'high' if z_score > 3 else 'medium'
                })
        
        return anomalies
```

**Pros:**
- ✅ No external dependencies
- ✅ Simple to implement
- ✅ Fast
- ✅ Good for basic statistical detection

**Cons:**
- ❌ Less sophisticated than NixtlaClient
- ❌ No seasonality detection
- ❌ No trend analysis

### Option 2: NixtlaClient Integration

Add NixtlaClient for advanced anomaly detection:

```python
from nixtla import NixtlaClient
import pandas as pd

class NixtlaAnomalyDetector:
    """NixtlaClient-based anomaly detector"""
    
    def __init__(self, api_key: str):
        self.client = NixtlaClient(api_key=api_key)
    
    def detect_anomalies(self, 
                        timestamps: List[datetime],
                        values: List[float],
                        freq: str = "H"):
        """Detect anomalies using NixtlaClient"""
        # Prepare time series data
        df = pd.DataFrame({
            'ds': timestamps,
            'y': values
        })
        
        # Detect anomalies
        result = self.client.detect_anomalies(
            df=df,
            freq=freq,
            model="auto_arima"
        )
        
        return result.anomalies  # Returns anomaly scores and flags
```

**Pros:**
- ✅ Advanced statistical models
- ✅ Seasonality detection
- ✅ Trend analysis
- ✅ High accuracy
- ✅ Multiple anomaly types

**Cons:**
- ❌ Requires API key (may have costs)
- ❌ External dependency
- ❌ Requires sufficient historical data
- ❌ More complex setup

### Option 3: Hybrid Approach (Recommended)

Combine both approaches:

```python
class HybridAnomalyDetector:
    """Hybrid threshold + statistical detection"""
    
    def __init__(self, 
                 thresholds: Dict[str, float],
                 use_statistical: bool = True):
        self.thresholds = thresholds
        self.statistical_detector = (
            NixtlaAnomalyDetector(api_key="...") if use_statistical 
            else SimpleAnomalyDetector()
        )
    
    def detect(self, metric_name: str, value: float, 
               historical_values: List[float]):
        """Detect anomalies using both methods"""
        anomalies = []
        
        # 1. Threshold-based (critical alerts)
        threshold = self.thresholds.get(metric_name)
        if threshold and value > threshold:
            anomalies.append({
                'type': 'threshold',
                'severity': 'critical',
                'value': value,
                'threshold': threshold
            })
        
        # 2. Statistical (subtle anomalies)
        if len(historical_values) >= 100:  # Need enough history
            stat_anomalies = self.statistical_detector.detect_anomalies(
                historical_values
            )
            anomalies.extend(stat_anomalies)
        
        return anomalies
```

---

## Recommendation for DocEX

### Phase 1: Enhance Threshold-Based Detection (Immediate)

Add simple statistical detection without NixtlaClient:

```python
# Add to VectorDatabaseMonitor
class VectorDatabaseMonitor:
    def _detect_statistical_anomalies(self, 
                                     metric_name: str,
                                     recent_values: List[float]):
        """Detect statistical anomalies using Z-score"""
        if len(recent_values) < 24:
            return []  # Need at least 24 data points
        
        mean = np.mean(recent_values)
        std = np.std(recent_values)
        
        if std == 0:
            return []  # No variation
        
        # Check last value
        last_value = recent_values[-1]
        z_score = abs((last_value - mean) / std)
        
        if z_score > 2.5:  # 2.5 standard deviations
            return [{
                'metric': metric_name,
                'value': last_value,
                'mean': mean,
                'z_score': z_score,
                'severity': 'high' if z_score > 3 else 'medium'
            }]
        
        return []
```

**Benefits:**
- ✅ No external dependencies
- ✅ Detects subtle anomalies
- ✅ Works with existing DocEX data
- ✅ Low overhead

### Phase 2: Add NixtlaClient (If Needed)

Only if Phase 1 isn't sufficient and you need:
- Seasonality detection
- Trend analysis
- Advanced pattern recognition

---

## Example: Detecting Gradual Performance Degradation

### Current (Threshold-Based):
```python
# Problem: Latency gradually increases from 500ms to 950ms over a week
# Threshold: 1000ms
# Result: No alert (still below threshold)
# Issue: Performance degraded 90% but no detection
```

### With Statistical Detection:
```python
# Same scenario
# Statistical model detects:
# - "Latency has increased 90% over past week"
# - "Current latency is 2.3 standard deviations above baseline"
# - "Trend anomaly: increasing faster than historical patterns"
# Result: Alert triggered before hitting threshold
```

---

## Cost-Benefit Analysis

### Threshold-Based (Current)
- **Cost:** $0 (already built)
- **Benefit:** Detects clear anomalies
- **ROI:** High (already implemented)

### Simple Statistical (Phase 1)
- **Cost:** Low (few hours of development)
- **Benefit:** Detects subtle anomalies
- **ROI:** High (significant improvement, low cost)

### NixtlaClient (Phase 2)
- **Cost:** Medium (API costs + integration time)
- **Benefit:** Advanced pattern detection
- **ROI:** Medium (only if you need advanced features)

---

## Conclusion

**For Anomaly Detection:**

1. **Start with enhanced threshold-based detection** ✅
   - Add simple statistical detection (Z-score)
   - No external dependencies
   - Detects most anomalies

2. **Consider NixtlaClient only if you need:**
   - Seasonality detection
   - Trend analysis
   - Advanced pattern recognition
   - Predictive anomaly detection

3. **Hybrid approach is best** ✅
   - Threshold-based for critical alerts
   - Statistical for subtle anomalies
   - Best of both worlds

**Recommendation: Enhance DocEX's existing detection with simple statistical methods first. Only add NixtlaClient if you specifically need advanced time series forecasting and pattern recognition.**


