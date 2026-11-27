# Sources

| Source | Version | Used for | Rights |
|---|---|---|---|
| Microsoft Support, "PMT function" and "FV function" | Pages current 2026-11 | Payment and future-value formulas: PMT = -(rate x (pv x (1+rate)^n + fv)) / ((1 + rate x type) x ((1+rate)^n - 1)); rate 0 gives -(pv+fv)/n | Cited, not copied |
| Microsoft Support, "ROUND function" | Pages current 2026-11 | ROUND rounds half away from zero; negative digits round left of the decimal point | Cited, not copied |
| Python `sqlite3` and SQLite | SQLite version is printed in every result's `engine` field | SQL execution | Public domain (SQLite), PSF license (Python) |
| Python | Version printed in `engine`; tested on 3.9.6 and 3.14.7 | Code execution | PSF license |

The formulas were checked against hand calculations in the unit tests (for example FV(0.04/12, 24, -100) = 2494.29 worked by hand).
