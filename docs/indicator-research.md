# Research Summary: Predicting Short-Term BTC Market Movements (15-min Interval)

This document synthesizes findings from research papers on predicting cryptocurrency price movements for short intervals (e.g., 15 minutes), focusing on methods and indicators that have demonstrated effectiveness.

## Key Predictors & Methods

### 1. Limit Order Book (LOB) Microstructure Analysis
*   **Core Idea:** LOB data provides a granular view of immediate supply and demand, revealing buying/selling pressure.
*   **Techniques:**
    *   **Deep Learning on LOB Data:** Models using Transformers (e.g., TLOB) and CNNs are employed to learn patterns directly from order flow sequences.
    *   **Order Flow Analysis:** Examining the sequence, size, and timing of executed trades.
    *   **Spoofing Detection:** Identifying manipulative order placements.
*   **Findings:** LOB analysis offers predictive signals by capturing short-term pressure shifts that traditional indicators might miss.
*   **References:**
    *   Shi et al. (2021): "Modelling Universal Order Book Dynamics in Bitcoin Market"
    *   Jha et al. (2020): "Deep Learning for Digital Asset Limit Order Books"
    *   Lensky & Hao (2024): "Learning to Predict Short-Term Volatility with Order Flow Image Representation"

### 2. Hybrid Indicator Approaches
*   **Core Idea:** Combining LOB features with traditional technical indicators enhances predictive accuracy.
*   **Effective Indicators:**
    *   **RSI (Relative Strength Index):** Measures momentum and overbought/oversold conditions.
    *   **VWAP (Volume Weighted Average Price):** Key benchmark for intraday price levels; deviation is a strong short-term signal.
    *   **Momentum:** Captures rapid price changes over very short periods (e.g., 60 seconds).
    *   **Short-term Moving Averages:** Gauge immediate trend direction.

### Demonstrated Effectiveness ("What has worked"):
*   **Microstructure Focus:** Models adept at processing LOB data and order flow sequences (e.g., Transformers) improve short-term predictions.
*   **Multi-feature Fusion:** Combining order book data with traditional indicators provides more robust signals.
*   **Volatility Prediction:** Accurately forecasting short-term volatility aids risk management and trade execution.

### Cautionary Notes ("What hasn't worked" / Pitfalls):
*   **Certainty is Unattainable:** All prediction models are probabilistic; the goal is a consistent edge, not perfect foresight.
*   **Overfitting:** Models trained on historical data may fail with changing market dynamics.
*   **Ignoring Order Flow:** Relying solely on price/volume without LOB depth can miss crucial short-term signals.
*   **Transaction Costs:** Frequent trading on short intervals can be negated by fees/slippage if not managed.

---
**Research Papers Reviewed:**
- ArXiv papers related to Bitcoin LOB prediction, cryptocurrency order book price movement prediction. Keywords used: "bitcoin limit order book prediction", "cryptocurrency order book predict price movement".

**Last Updated:** 2026-02-03
