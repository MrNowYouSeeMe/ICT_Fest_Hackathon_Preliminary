# Tests Run Report

## Purpose
This document summarizes the local verification performed after fixing the API bugs.

The tests were black-box style HTTP API checks against the running FastAPI server. The goal was to verify that the implementation follows the README business rules and preserves the API contract.

---

## Overall Result

Final retest: 64 PASS, 0 FAIL  
Deep corner/concurrency: 90 PASS, 0 FAIL  
README max audit after patch: 60 PASS, 0 FAIL  
Total checked: 214 PASS, 0 FAIL

---

## Test Environment

- Application: CoWork FastAPI booking API
- Server: local Uvicorn server
- Base URL: `http://127.0.0.1:8000`
- Database: local SQLite test database
- Test style: black-box HTTP API requests
- Test scripts: temporary local Python scripts, not committed

---

## 1. Final Retest

Result:

`64 PASS, 0 FAIL`

### Covered Areas
- health endpoint
- registration
- duplicate username rejection
- login success/failure
- refresh token rotation
- refresh token reuse rejection
- logout and revoked access token rejection
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

---

## 2. Deep Corner and Concurrency Retest

Result:

`90 PASS, 0 FAIL`

### Covered Areas
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

---

## 3. README Max Audit After Patch

Result:

`60 PASS, 0 FAIL`

### Covered Areas
- refresh token lifetime exactly 7 days
- usage report with no rooms
- usage report including newly created zero-booking rooms immediately
- usage report inclusive date range
- usage report excluding cancelled bookings immediately
- admin export with cross-organization room id returning 404
- admin export default behavior
- admin export include_all behavior
- concurrent quota enforcement
- concurrent rate-limit enforcement

---

## Authentication Tests

Verified:
- access token includes required claims
- refresh token includes required claims
- access token lifetime is exactly 900 seconds
- refresh token lifetime is 7 days
- missing/invalid/expired tokens return 401
- refresh token cannot be used as access token
- access token cannot be used as refresh token
- logout invalidates access token
- refresh token reuse is rejected

---

## Multi-Tenancy Tests

Verified:
- users only see rooms in their own organization
- cross-org room booking returns 404
- cross-org stats returns 404
- cross-org availability returns 404
- cross-org export room_id returns 404
- members cannot read another member's booking
- members cannot cancel another member's booking
- admins can access bookings inside their own organization only

---

## Booking Validation Tests

Invalid cases verified:
- past booking start
- end time equal to start time
- end time before start time
- zero-duration booking
- non-whole-hour duration
- duration longer than 8 hours
- missing required fields produce FastAPI 422 validation response

Valid cases verified:
- 1-hour booking
- 8-hour booking
- naive datetime treated as UTC
- timezone offset input converted to UTC
- correct price calculation
- response datetimes include explicit UTC designator

---

## Conflict Tests

Verified:
- exact same interval conflicts
- inside overlap conflicts
- covering overlap conflicts
- back-to-back before an existing booking is allowed
- back-to-back after an existing booking is allowed

Expected conflict:
`409 ROOM_CONFLICT`

---

## Quota Tests

Verified:
- first 3 bookings in `(now, now + 24h]` are allowed
- 4th booking inside the window is rejected
- booking outside the 24-hour quota window is allowed
- concurrent quota requests allow at most 3 successful bookings

Expected quota failure:
`409 QUOTA_EXCEEDED`

---

## Rate-Limit Tests

Verified:
- more than 20 booking attempts within rolling 60 seconds are rejected
- failed booking requests also count toward the rate limit
- concurrent rate-limit requests hold correctly

Expected rate-limit failure:
`429 RATE_LIMITED`

---

## Cancellation and Refund Tests

Verified:
- owner can cancel own booking
- admin can cancel organization booking
- another member cannot cancel someone else's booking
- duplicate cancellation is rejected
- exactly one refund log is created
- refund policy returns 100%, 50%, and 0% correctly
- cancel response amount equals stored refund log amount
- half-cent rounding is rounded up

Verified rounding example:
`50% of 1001 cents = 501 cents`

Expected duplicate cancellation:
`409 ALREADY_CANCELLED`

---

## Pagination Tests

Verified:
- page starts from 1
- limit must be between 1 and 100
- page 0 returns validation error
- limit 101 returns validation error
- offset calculation is correct
- results are sorted by ascending start time and ascending id
- sequential pages do not skip or repeat items
- total count is included

---

## Usage Report Tests

Verified:
- report returns per-room usage for caller organization
- rooms with zero bookings are included
- newly created zero-booking rooms appear immediately
- date range is inclusive
- cancelled bookings are excluded
- report reflects current state immediately
- invalid date format returns 400
- reversed date range returns 400

---

## Availability and Stats Tests

Verified:
- availability returns confirmed bookings for the UTC date
- availability is sorted
- cancelled bookings are removed from availability
- room stats reflect current confirmed booking count
- room stats revenue decreases after cancellation
- stats always match confirmed bookings in the database

---

## Admin Export Tests

Verified:
- admin export succeeds
- member export is forbidden
- export CSV header remains exact
- export is organization-scoped
- cross-organization `room_id` returns 404
- default export includes only the admin user's bookings
- `include_all=true` includes all organization bookings

Expected CSV header:
`id,reference_code,room_id,user_id,start_time,end_time,status,price_cents`

---

## Concurrency Tests

### Same-Slot Booking Race
Multiple concurrent requests attempted to book the same room and same time.

Expected:
- exactly 1 success
- remaining requests return `409 ROOM_CONFLICT`

Verified:
`PASS`

### Quota Race
Multiple concurrent requests attempted to create bookings within the next 24 hours.

Expected:
- at most 3 successful bookings
- remaining requests return `409 QUOTA_EXCEEDED`

Verified:
`PASS`

### Reference Code Race
Multiple concurrent successful bookings were created in different slots.

Expected:
- all reference codes are unique

Verified:
`PASS`

### Cancellation Race
Multiple concurrent requests attempted to cancel the same booking.

Expected:
- exactly 1 success
- remaining requests return `409 ALREADY_CANCELLED`
- exactly 1 refund log exists

Verified:
`PASS`

### Rate-Limit Race
Multiple concurrent booking attempts were sent for the same user.

Expected:
- only 20 requests accepted in rolling 60 seconds
- excess requests return `429 RATE_LIMITED`

Verified:
`PASS`

---

## Final Conclusion

Final retest: 64 PASS, 0 FAIL  
Deep corner/concurrency: 90 PASS, 0 FAIL  
README max audit after patch: 60 PASS, 0 FAIL  
Total checked: 214 PASS, 0 FAIL
