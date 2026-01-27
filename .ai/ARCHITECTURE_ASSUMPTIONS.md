# Architecture Assumptions
**Date:** 2026-01-27  
**Purpose:** Document architectural assumptions and design decisions

## 🔒 Thread Safety Assumptions

### **Single-Threaded Execution**
**Assumption:** The trading bot runs in a single-threaded execution model.

**Rationale:**
- Trading logic requires sequential processing of market data
- Strategy selection and prediction generation must be atomic
- WebSocket data processing is event-driven but sequential
- SQLite database operations benefit from single-threaded access

**Implications:**
- No thread synchronization needed for core trading logic
- Market data updates are processed sequentially
- Strategy selection is not concurrent
- Position management is single-threaded

**Future Considerations:**
- If multi-threading is needed, consider:
  - Separate threads for WebSocket handling (already done)
  - Thread-safe data structures for shared state
  - Locking mechanisms for critical sections
  - Queue-based communication between threads

**Current Implementation:**
- Main loop: `SessionOrchestrator._main_data_loop()` - single-threaded
- WebSocket handlers: Separate threads for data reception
- Database: SQLite with file-level locking (single writer)

---

## 📊 Data Structure Assumptions

### **Orderbook Data Structure**
**Assumption:** Orderbook data follows a consistent nested structure:
```python
{
    "orderbook_analysis": {
        "bid_ask_spread": {
            "percentage": float,
            "absolute": float,
            "category": str
        },
        "liquidity_depth": {
            "depth_score": float
        }
    }
}
```

**Validation:** Uses `_require_key()` for strict validation (NO FALLBACKS)

**Rationale:**
- Orderbook analyzer guarantees structure
- MarketDataService validates at boundary
- Direct access is safe after validation

---

### **Trend Data Structure**
**Assumption:** Trend data always includes required fields:
```python
{
    "direction": str,  # "BULLISH", "BEARISH", "SIDEWAYS"
    "strength": float,  # 0.0-1.0
    "detailed_timeframes": {...}
}
```

**Validation:** Uses `_require_key()` for strict validation (NO FALLBACKS)

**Rationale:**
- Trend calculator guarantees structure
- MarketDataService validates at boundary
- No fallback values needed

---

## 🔄 Execution Flow Assumptions

### **Sequential Data Processing**
**Assumption:** Market data is processed in a specific order:
1. Raw data fetching (parallel)
2. Analysis module updates (sequential)
3. Strategy selection (single-threaded)
4. Prediction generation (single-threaded)
5. Position management (single-threaded)

**Rationale:**
- Each step depends on previous step's output
- Strategy selection needs complete market analysis
- Predictions need strategy decision
- Positions need predictions

---

## 🛡️ Error Handling Assumptions

### **NO FALLBACKS Policy**
**Assumption:** All critical data must be present or system fails loudly.

**Rationale:**
- Missing data indicates system failure
- Fallback values mask problems
- Confidence calculation requires real data
- Trading decisions must be based on valid data

**Implementation:**
- Use `_require_key()` for validation
- Raise exceptions on missing data
- No default values for critical fields
- Error propagation instead of silent failures

---

## 📈 Performance Assumptions

### **Cache Invalidation**
**Assumption:** Cache invalidation is strategy-independent for most data.

**Rationale:**
- Market data (RSI, trend, volume) is strategy-independent
- Only S/R levels are strategy-dependent
- Pattern recognition is strategy-independent
- Reduces cache complexity

**Implementation:**
- Most data cached without strategy key
- S/R levels cached per strategy
- TTL-based expiration
- Manual invalidation on candle boundaries

---

## 🔐 Security Assumptions

### **Environment Variables**
**Assumption:** Sensitive data (API keys, secrets) stored in `.env` file.

**Rationale:**
- Never commit secrets to git
- Environment-specific configuration
- Easy to rotate credentials
- Standard practice

**Implementation:**
- `.env` file in `.gitignore`
- `env_example.txt` for documentation
- SystemInitializer creates `.env` if missing

---

## 📝 Documentation Assumptions

### **Code Comments**
**Assumption:** Complex logic requires inline documentation.

**Rationale:**
- Trading logic is domain-specific
- Mathematical formulas need explanation
- Strategy decisions need context
- Future maintainers need guidance

**Implementation:**
- Docstrings for all public methods
- Inline comments for complex calculations
- NO FALLBACKS comments for policy enforcement
- Type hints for clarity

---

**Last Updated:** 2026-01-27
