# Bug Report

## Project
CoWork multi-tenant coworking space booking API.

## Objective
The goal was to fix the existing broken API implementation while preserving the original API contract exactly: paths, status codes, error codes, JSON field names, JWT claims, and response shapes.

No new feature was added. The fixes focus only on correctness, business rules, multi-tenancy, authentication, booking behavior, refunds, reports, exports, and concurrency safety.

---

## 1. Duplicate Username Registration

File: `app/routers/auth.py`

### Bug
Registering the same username inside the same organization returned a successful `201` response.

### Why it was wrong
Usernames must be unique inside each organization.

### Fix
Added organization-scoped duplicate username validation.

### Expected behavior
- Status: `409`
- Code: `USERNAME_TAKEN`

---

## 2. Access Token Lifetime

File: `app/auth.py`

### Bug
Access token lifetime was calculated incorrectly.

### Why it was wrong
Access tokens must have `exp - iat = exactly 900 seconds`.

### Fix
Corrected the access token expiry calculation.

---

## 3. Logout Token Revocation

File: `app/auth.py`

### Bug
Logout stored the access token `jti`, but token validation checked the wrong claim.

### Why it was wrong
A logged-out access token could still be used.

### Fix
Revoked access tokens are now checked by `jti`.

---

## 4. Refresh Token Reuse

Files:
- `app/auth.py`
- `app/routers/auth.py`

### Bug
The same refresh token could be reused multiple times.

### Why it was wrong
Refresh tokens must be single-use.

### Fix
Added refresh token `jti` consumption tracking. Reusing an old refresh token now returns `401`.

---

## 5. Datetime Normalization

File: `app/timeutils.py`

### Bug
Datetime timezone offsets were discarded instead of converted.

### Why it was wrong
All API datetimes carrying a UTC offset must be converted to UTC before storage or comparison.

### Fix
Timezone-aware datetime inputs are now converted to UTC before internal storage.

---

## 6. Invalid Booking Window Validation

File: `app/routers/bookings.py`

### Bug
Invalid booking windows could pass validation:
- past start time had a grace window
- `end_time <= start_time` could pass
- zero-duration booking could pass
- non-whole-hour duration could pass
- duration range validation was incomplete

### Why it was wrong
Booking duration must be a whole number of hours, minimum 1 and maximum 8. `start_time` must be strictly in the future.

### Fix
Added strict validation for:
- `start_time > now`
- `end_time > start_time`
- whole-hour duration
- duration from 1 to 8 hours

### Expected behavior
Invalid booking windows return:
- Status: `400`
- Code: `INVALID_BOOKING_WINDOW`

---

## 7. Booking Conflict Logic

File: `app/routers/bookings.py`

### Bug
Back-to-back bookings were rejected as conflicts.

### Why it was wrong
Back-to-back bookings are allowed. Only real overlaps should conflict.

### Fix
Changed the overlap rule to strict overlap logic:

`existing.start_time < new.end_time AND new.start_time < existing.end_time`

### Expected behavior
Real overlaps return:
- Status: `409`
- Code: `ROOM_CONFLICT`

---

## 8. Booking Quota

File: `app/routers/bookings.py`

### Bug
Quota enforcement was not protected well enough during booking creation.

### Why it was wrong
A member may hold at most 3 confirmed bookings with start time in `(now, now + 24h]`, across all rooms in the organization.

### Fix
Quota check now runs inside the protected booking creation critical section.

### Expected behavior
Quota violation returns:
- Status: `409`
- Code: `QUOTA_EXCEEDED`

---

## 9. Rate Limit

File: `app/services/ratelimit.py`

### Bug
The rate-limit bucket was not concurrency-safe.

### Why it was wrong
`POST /bookings` is limited to 20 requests per rolling 60 seconds per user. All requests must count, successful or not, and this must hold under concurrent requests.

### Fix
Added locking around the rolling-window rate-limit state.

### Expected behavior
Excess requests return:
- Status: `429`
- Code: `RATE_LIMITED`

---

## 10. Booking Visibility

File: `app/routers/bookings.py`

### Bug
A member could access another member's booking inside the same organization.

### Why it was wrong
Members may read and cancel only their own bookings. Admins may read and cancel any booking in their organization.

### Fix
Added member ownership checks for booking read and cancellation.

### Expected behavior
Another member's booking returns:
- Status: `404`
- Code: `BOOKING_NOT_FOUND`

---

## 11. Booking Detail `start_time`

File: `app/routers/bookings.py`

### Bug
`GET /bookings/{id}` returned `created_at` as `start_time`.

### Why it was wrong
The endpoint must return the actual booking start time.

### Fix
Removed the incorrect overwrite and used the booking serializer correctly.

---

## 12. Pagination and Ordering

File: `app/routers/bookings.py`

### Bug
Pagination had multiple issues:
- wrong ordering
- wrong offset
- requested `limit` ignored

### Why it was wrong
`GET /bookings` must return the caller's own bookings sorted by ascending `start_time`, tie-break by ascending `id`, using offset `(page - 1) * limit`.

### Fix
Corrected ordering, offset, limit, and total count.

---

## 13. Refund Policy

Files:
- `app/routers/bookings.py`
- `app/services/refunds.py`

### Bug
Refund tier logic and rounding were wrong.

### Why it was wrong
Required refund policy:
- notice >= 48h: 100%
- 24h <= notice < 48h: 50%
- notice < 24h: 0%

Half-cent values must round up.

### Fix
Corrected refund tier logic and used integer half-up cent rounding.

### Verified example
`50% of 1001 cents = 501 cents`

---

## 14. Duplicate Cancellation / Refund Log

File: `app/routers/bookings.py`

### Bug
Concurrent or repeated cancellation could risk incorrect refund behavior.

### Why it was wrong
A cancelled booking must have exactly one `RefundLog`, and the cancel response amount must equal the stored refund amount.

### Fix
Cancellation now runs inside a protected critical section.

### Expected behavior
Repeated cancellation returns:
- Status: `409`
- Code: `ALREADY_CANCELLED`

---

## 15. Reference Code Uniqueness

File: `app/services/reference.py`

### Bug
Reference code generation used shared mutable state without synchronization.

### Why it was wrong
Every booking's `reference_code` must be unique, including under concurrent creation.

### Fix
Added locking around reference code generation.

---

## 16. Notification Side Effects

File: `app/services/notifications.py`

### Bug
Notification simulation had unnecessary delay and locking behavior.

### Why it was risky
It could slow down concurrent requests and increase liveness risk.

### Fix
Simplified notification hooks to safe no-op functions.

---

## 17. Room Stats Accuracy

File: `app/routers/rooms.py`

### Bug
Room stats depended on fragile in-memory state.

### Why it was wrong
Room stats must always equal the values derivable from confirmed bookings in the database.

### Fix
Room stats are now computed directly from confirmed bookings in the database.

---

## 18. Availability Freshness

File: `app/routers/bookings.py`

### Bug
Availability could become stale after booking creation or cancellation.

### Why it was wrong
Availability must reflect current confirmed bookings immediately.

### Fix
Booking creation and cancellation now invalidate related availability cache entries.

---

## 19. Admin Export Organization Scoping

File: `app/services/export.py`

### Bug
Admin export could bypass organization scoping in some code paths.

### Why it was wrong
Admins must only export bookings from their own organization.

### Fix
Export queries now always join through `Room` and filter by caller organization.

---

## 20. Concurrency Safety

Files:
- `app/routers/bookings.py`
- `app/services/reference.py`
- `app/services/ratelimit.py`
- `app/services/stats.py`

### Bug
Critical shared operations were not safe under concurrent requests.

### Fix
Added locks around:
- booking conflict check and creation
- quota check
- cancellation and refund
- reference generation
- rate-limit bucket updates
- stats updates

---

## 21. Usage Report Immediate Freshness

File: `app/routers/admin.py`

### Bug
`GET /admin/usage-report` could return stale cached data after a new room was created. A newly created room with zero bookings was not immediately shown in the report.

### Why it was wrong
Usage report must return every room in the caller's organization, including rooms with zero bookings, and must reflect the current state immediately.

### Fix
Rewrote usage report to compute directly from the database on every request.

---

## 22. Admin Export Cross-Organization `room_id`

File: `app/routers/admin.py`

### Bug
`GET /admin/export?room_id=<cross-org-room>` returned an empty CSV instead of treating the cross-organization room as non-existent.

### Why it was wrong
Cross-organization resource IDs must behave as non-existent.

### Fix
Added organization-scoped room validation before export.

### Expected behavior
Cross-org `room_id` now returns:
- Status: `404`
- Code: `ROOM_NOT_FOUND`

---

## Verification Summary

Final retest: 64 PASS, 0 FAIL  
Deep corner/concurrency: 90 PASS, 0 FAIL  
README max audit after patch: 60 PASS, 0 FAIL  
Total checked: 214 PASS, 0 FAIL

Detailed testing summary is available in `TESTS_RUN.md`.
