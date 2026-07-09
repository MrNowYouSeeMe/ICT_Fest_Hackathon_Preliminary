# Tests Run Report

## Purpose
This document summarizes the local API tests performed after fixing the business-rule bugs.

The tests were black-box style API tests against the running FastAPI server. The goal was to verify correctness without depending on internal implementation details.

---

## Overall Result

Final local black-box retest:
64 PASS, 0 FAIL

Deep corner and concurrency retest:
90 PASS, 0 FAIL

Total local verification:
154 PASS, 0 FAIL

---

## Test Environment
- Application: CoWork FastAPI booking API
- Server: local Uvicorn server
- Base URL: `http://127.0.0.1:8000`
- Database: local SQLite test database
- Test style: black-box HTTP API requests
- Test scripts: temporary local Python scripts, not committed

---

## Final Retest Coverage

The first retest contained 64 checks and passed fully.

Covered:
- health endpoint
- registration
- duplicate username rejection
- login success/failure
- refresh token rotation
- refresh token reuse rejection
- logout and revoked token rejection
- admin/member permission checks
- room creation permission
- cross-organization isolation
- booking invalid window validation
- room conflict detection
- back-to-back booking behavior
- price calculation
- booking detail correctness
- member vs admin booking visibility
- refund 100%, 50%, and 0%
- refund rounding
- duplicate cancellation rejection
- room stats
- availability
- pagination
- admin export
- rate limiting

Result:
64 PASS, 0 FAIL

---

## Deep Corner and Concurrency Retest Coverage

The second retest contained 90 checks and passed fully.

Covered:
- JWT claim existence
- access token lifetime exactly 900 seconds
- missing bearer token rejection
- wrong token type rejection
- access token used as refresh token rejection
- refresh token used as access token rejection
- cross-organization stats isolation
- cross-organization availability isolation
- invalid availability date validation
- 1-hour valid booking
- 8-hour valid booking
- zero-duration invalid booking
- non-whole-hour invalid booking
- 9-hour invalid booking
- timezone offset conversion to UTC
- same interval conflict
- inside overlap conflict
- back-to-back before existing booking
- back-to-back after existing booking
- quota limit inside next 24 hours
- booking outside 24-hour quota window
- member cancellation permission
- admin cancellation permission
- refund log uniqueness
- page 0 validation
- limit greater than 100 validation
- failed booking requests counted toward rate limit
- concurrent same-slot booking race
- concurrent reference code uniqueness
- concurrent duplicate cancellation race

Result:
90 PASS, 0 FAIL

---

## Authentication Tests

Verified:
- Access token includes required claims.
- Access token lifetime is exactly 900 seconds.
- Missing bearer token returns 401.
- Refresh token cannot be used as access token.
- Access token cannot be used as refresh token.
- Logout invalidates access token.
- Refresh token reuse is rejected.

---

## Multi-Tenancy Tests

Verified:
- Cross-organization room booking is hidden.
- Cross-organization stats return 404.
- Cross-organization availability returns 404.
- Members cannot read other members' bookings.
- Members cannot cancel other members' bookings.
- Admins can access bookings inside their own organization only.

---

## Booking Validation Tests

Invalid cases verified:
- past booking start
- end time before start time
- zero-duration booking
- non-whole-hour duration
- duration longer than 8 hours

Valid cases verified:
- 1-hour booking
- 8-hour booking
- timezone offset input converted to UTC
- correct price calculation

---

## Conflict Tests

Verified:
- same interval booking returns conflict
- inside overlap returns conflict
- touching before an existing booking is allowed
- touching after an existing booking is allowed

Expected conflict:
409 ROOM_CONFLICT

---

## Quota Tests

Verified:
- first 3 bookings within next 24 hours are allowed
- 4th booking within next 24 hours is rejected
- booking outside the 24-hour quota window is allowed

Expected quota failure:
409 QUOTA_EXCEEDED

---

## Rate-Limit Tests

Verified:
- more than 20 booking attempts within rolling 60 seconds is rejected
- failed booking requests also count toward the rate limit

Expected rate-limit failure:
429 RATE_LIMITED

---

## Cancellation and Refund Tests

Verified:
- owner can cancel own booking
- admin can cancel organization booking
- another member cannot cancel someone else's booking
- duplicate cancellation is rejected
- exactly one refund log is created
- refund policy returns 100%, 50%, and 0% correctly
- half-cent rounding is rounded up

Verified rounding example:
50% of 1001 cents = 501 cents

---

## Pagination Tests

Verified:
- page starts from 1
- limit must be between 1 and 100
- page 0 returns validation error
- limit 101 returns validation error
- offset calculation is correct
- results are sorted by start time ascending and id ascending
- total count is included

---

## Availability and Stats Tests

Verified:
- availability returns confirmed bookings for the UTC date
- availability is sorted
- cancelled booking is removed from current availability
- room stats reflect confirmed booking count
- room stats revenue decreases after cancellation

---

## Admin Export Tests

Verified:
- admin export succeeds
- member export is forbidden
- export header remains stable
- export is organization-scoped

---

## Concurrency Tests

Same-slot booking race:
- Multiple concurrent requests tried to book the same room and same time.
- Result: exactly 1 success, remaining requests returned 409 conflict.

Reference code race:
- Multiple concurrent successful bookings were created in different slots.
- Result: all reference codes were unique.

Cancellation race:
- Multiple concurrent requests tried to cancel the same booking.
- Result: exactly 1 success, remaining requests returned 409, and exactly 1 refund log existed.

---

## Final Conclusion

All local verification passed.

Final local black-box retest:
64 PASS, 0 FAIL

Deep corner and concurrency retest:
90 PASS, 0 FAIL

Combined:
154 PASS, 0 FAIL
