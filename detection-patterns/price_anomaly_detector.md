# Price Anomaly Detection Pattern

## Overview

Detects government contracts or purchases priced significantly above or below market rates, which may indicate inflated pricing fraud, kickbacks, or other procurement irregularities.

## Pattern Type
**Discovery Pattern** - Automated anomaly detection

## Fraud Indicators

This pattern flags potential fraud when:
- Contract price >2 standard deviations above comparable contracts
- Price per unit significantly exceeds market rates
- Similar services purchased at vastly different prices by same agency
- Prices inconsistent with published GSA schedules

## Data Sources

### Primary Sources
1. **USAspending.gov** - Federal contract data
   - API: https://api.usaspending.gov/
   - Fields: award amount, vendor, description, dates

2. **GSA Schedules** - Government pricing benchmarks
   - URL: https://www.gsaadvantage.gov/
   - Baseline pricing for common services/goods

3. **State Procurement Databases**
   - Varies by state
   - Examples: NY Contract Reporter, CA eProcurement

### Comparison Sources
- Similar contracts in same jurisdiction
- Similar contracts in other jurisdictions
- GSA schedule pricing
- Commercial market rates (if available)

## Detection Algorithm

### Step 1: Data Collection
```python
def collect_contracts(jurisdiction, category, date_range):
    """
    Fetch contracts from data source
    Returns: List of contract records
    """
    contracts = fetch_from_usaspending(
        jurisdiction=jurisdiction,
        category=category,
        date_range=date_range
    )
    return contracts
```

### Step 2: Normalization
```python
def normalize_contract(contract):
    """
    Normalize contract data for comparison
    """
    return {
        'id': contract.award_id,
        'amount': float(contract.amount),
        'description': standardize_description(contract.description),
        'category': categorize_service(contract.description),
        'vendor': normalize_vendor_name(contract.vendor),
        'agency': contract.agency,
        'date': contract.award_date,
        'quantity': extract_quantity(contract),
        'unit_price': calculate_unit_price(contract)
    }
```

### Step 3: Comparison Group Selection
```python
def select_comparables(target_contract, all_contracts):
    """
    Select similar contracts for comparison
    """
    comparables = []

    for contract in all_contracts:
        similarity_score = calculate_similarity(
            target_contract,
            contract
        )

        # Only use sufficiently similar contracts
        if similarity_score > 0.7:
            comparables.append(contract)

    return comparables
```

### Step 4: Statistical Analysis
```python
def detect_price_anomaly(target_contract, comparables):
    """
    Statistical analysis to detect outliers
    """
    if len(comparables) < 5:
        return None  # Insufficient data

    # Calculate statistics for comparable contracts
    comparable_prices = [c['unit_price'] for c in comparables]

    mean_price = statistics.mean(comparable_prices)
    std_dev = statistics.stdev(comparable_prices)
    median_price = statistics.median(comparable_prices)

    target_price = target_contract['unit_price']

    # Calculate z-score
    z_score = (target_price - mean_price) / std_dev

    # Calculate percentage difference
    pct_diff_from_mean = ((target_price - mean_price) / mean_price) * 100
    pct_diff_from_median = ((target_price - median_price) / median_price) * 100

    # Detection thresholds
    is_anomaly = (
        abs(z_score) > 2.0 or  # >2 standard deviations
        abs(pct_diff_from_median) > 30  # >30% from median
    )

    if is_anomaly:
        return {
            'anomaly_type': 'price_anomaly',
            'direction': 'high' if target_price > mean_price else 'low',
            'z_score': z_score,
            'target_price': target_price,
            'mean_price': mean_price,
            'median_price': median_price,
            'std_dev': std_dev,
            'pct_diff_from_mean': pct_diff_from_mean,
            'pct_diff_from_median': pct_diff_from_median,
            'comparable_count': len(comparables),
            'confidence': calculate_confidence(z_score, len(comparables))
        }

    return None
```

### Step 5: Confidence Scoring
```python
def calculate_confidence(z_score, sample_size):
    """
    Calculate confidence in the anomaly detection
    """
    # Base confidence on z-score magnitude
    z_confidence = min(abs(z_score) / 5.0, 1.0)  # Cap at z=5

    # Adjust for sample size
    if sample_size >= 20:
        size_factor = 1.0
    elif sample_size >= 10:
        size_factor = 0.8
    elif sample_size >= 5:
        size_factor = 0.6
    else:
        size_factor = 0.3

    confidence = z_confidence * size_factor

    # Cap between 0.3 and 0.95
    return max(0.3, min(0.95, confidence))
```

## Example Finding

### Input Contract
```json
{
  "award_id": "CONT_AWD_12345_9700_SPE4A123F1234_9700",
  "amount": 250000.00,
  "description": "IT Help Desk Support Services",
  "vendor": "ABC Tech Solutions LLC",
  "agency": "Department of Transportation",
  "award_date": "2025-10-15",
  "quantity": "1 year contract",
  "unit_price": 250000.00
}
```

### Comparable Contracts (n=12)
- Mean price: $165,000
- Median price: $160,000
- Std dev: $25,000

### Detection Result
```json
{
  "anomaly_detected": true,
  "anomaly_type": "price_anomaly",
  "direction": "high",
  "z_score": 3.4,
  "target_price": 250000.00,
  "mean_price": 165000.00,
  "median_price": 160000.00,
  "pct_diff_from_mean": 51.5,
  "pct_diff_from_median": 56.25,
  "comparable_count": 12,
  "confidence": 0.82
}
```

### Generated Finding
```json
{
  "title": "IT Help Desk contract 51% above comparable rates - DoT",
  "description": "Department of Transportation awarded a contract for IT Help Desk Support Services at $250,000/year, which is 51.5% above the mean price of $165,000 for 12 comparable contracts and 56.25% above the median price of $160,000. This represents a statistical anomaly of 3.4 standard deviations above the mean.",
  "category": "procurement",
  "jurisdiction": "federal",
  "estimated_amount": 85000.00,
  "confidence": 0.82,
  "sources": [
    {
      "url": "https://www.usaspending.gov/award/CONT_AWD_12345...",
      "description": "Original contract award",
      "source_type": "government_db"
    },
    {
      "url": "https://www.usaspending.gov/search/?filters=...",
      "description": "Comparable contracts search results",
      "source_type": "government_db"
    }
  ],
  "evidence": {
    "type": "price_comparison",
    "data": {
      "target_price": 250000.00,
      "mean_comparable_price": 165000.00,
      "median_comparable_price": 160000.00,
      "standard_deviation": 25000.00,
      "z_score": 3.4,
      "comparable_contracts": 12,
      "difference_amount": 85000.00,
      "difference_percentage": 51.5
    }
  }
}
```

## Verification Checklist

When verifying a price anomaly finding, check:

1. **Source Accuracy**
   - [ ] Contract amount correctly extracted
   - [ ] Comparable contracts actually comparable
   - [ ] Dates align properly

2. **Calculation Verification**
   - [ ] Statistical calculations correct
   - [ ] Unit price normalization appropriate
   - [ ] Percentage calculations accurate

3. **Context Considerations**
   - [ ] Geographic cost differences (high cost of living areas)
   - [ ] Scope differences (24/7 support vs business hours)
   - [ ] Quality requirements (security clearances, certifications)
   - [ ] Market timing (supply constraints, emergency procurement)
   - [ ] Contract modifications (original vs amended)

4. **Alternative Explanations**
   - [ ] Unique requirements justifying higher price
   - [ ] Bundled services not apparent in description
   - [ ] Multi-year vs single-year contracts
   - [ ] Performance-based incentives
   - [ ] Data entry errors in source system

## False Positive Mitigation

Common false positives and how to avoid them:

### 1. Incomparable Contracts
**Problem**: Comparing dissimilar services
**Solution**: Stricter similarity scoring, more detailed categorization

### 2. Geographic Variations
**Problem**: NYC prices vs rural prices
**Solution**: Filter comparables by geographic region

### 3. Scope Differences
**Problem**: Basic vs premium service levels
**Solution**: Extract service level from descriptions

### 4. Time Periods
**Problem**: Comparing across different years
**Solution**: Limit comparables to recent contracts (e.g., last 2 years)

### 5. Data Quality Issues
**Problem**: Incorrect amounts in source data
**Solution**: Cross-reference with additional sources

## Implementation Checklist

- [ ] Set up data source connections
- [ ] Implement contract fetching
- [ ] Implement normalization logic
- [ ] Implement similarity scoring
- [ ] Implement statistical analysis
- [ ] Implement confidence scoring
- [ ] Add logging and monitoring
- [ ] Create test cases
- [ ] Document edge cases
- [ ] Set up error handling

## Performance Considerations

- **Data Volume**: Federal government awards 50,000+ contracts/year
- **Batch Processing**: Process in chunks to avoid memory issues
- **Caching**: Cache comparable contract sets for similar searches
- **Rate Limiting**: Respect API rate limits (USAspending: 100 req/min)

## Continuous Improvement

Track and improve:
- **Precision**: % of flagged contracts that are actual fraud
- **Recall**: % of actual fraud cases detected
- **False Positive Rate**: % of flags that are legitimate
- **Verification Outcomes**: Learn from verified findings

Adjust thresholds based on:
- Verification feedback
- Domain expert review
- Category-specific patterns
- Jurisdiction-specific norms

## Related Patterns

This pattern works well combined with:
- **Shell Company Detector**: Cross-check if vendor is legitimate
- **Conflict of Interest Detector**: Check for relationships
- **Timeline Anomaly Detector**: Check procurement timeline
- **Geographic Anomaly Detector**: Check vendor location vs work location

## References

- GSA Schedule pricing: https://www.gsaadvantage.gov/
- USAspending API docs: https://api.usaspending.gov/docs/
- Statistical anomaly detection: Z-score method
- Similar patterns used by: GAO, various Inspectors General

## License

This detection pattern is public domain and may be freely used, modified, and distributed.
