# Work Roster Insights (Step E)

* Total orders in enriched dataset: 128
* Share of orders on workdays (shift\_type != day off): 83.59%
* After-shift analysis: not enough matched records to compute.



### Context \& Methodology



This analysis examines food delivery orders in relation to recorded work roster data.



Orders are considered work-related only when they fall within defined working shift time windows.

Orders outside these windows are retained in the dataset but excluded from work-context analysis.



Work roster data was joined to orders using time-window-based matching rather than static keys.

Missing shift context values are expected and represent orders outside defined working periods.

This approach ensures that behavioral insights are derived only from contextually relevant data.



---

### &nbsp;Key Findings



\- Total orders in enriched dataset: 128

\- Share of orders on workdays (shift\_type != day off): 83.59%

\- After-shift analysis: not enough matched records to compute.



---





## Summary by shift\_type

* evenning shift: 75 orders, avg spend 28.64, median delivery 30.0 mins
* day off: 21 orders, avg spend 23.00, median delivery 47.0 mins
* morning shift: 1 orders, avg spend 28.99, median delivery 17.0 mins
* night shift: 1 orders, avg spend 13.99, median delivery nan mins
* 
