# Bug Report

## Project
CoWork multi-tenant coworking space booking API.

## Objective
The objective was to fix the existing API implementation while preserving the original API contract, response structure, status codes, error codes, authentication behavior, and business rules.

No new feature was added. The fixes focus on correctness, multi-tenancy, booking rules, refunds, pagination, reporting, and concurrency safety.

---

## 1. Duplicate Username Registration
File: `app/routers/auth.py`

Bug:
Registering the same username inside the same organization returned a successful 201 response.

Why it was wrong:
Usernames must be unique inside each organization.

Fix:
Added organization-scoped duplicate username validation.

Expected behavior:
- Status: 409
- Code: USERNAME_TAKEN

---

## 2. Access Token Lifetime
File: `app/auth.py`

Bug:
Access token lifetime was calculated incorrectly.

Why it was wrong:
Access tokens must live exactly 900 seconds.

Fix:
Corrected access token expiry calculation so that `exp - iat = 900`.

---

## 3. Logout Token Revocation
File: `app/auth.py`

Bug:
Logout stored the token `jti`, but validation checked the wrong claim.

Why it was wrong:
Logged-out access tokens could still be used.

Fix:
Revoked access tokens are now checked by `jti`.

---

## 4. Refresh Token Reuse
Files:
- `app/auth.py`
- `app/routers/auth.py`

Bug:
The same refresh token could be reused multiple times.

Why it was wrong:
Refresh tokens must be single-use.

Fix:
Added refresh token `jti` consumption tracking. Reusing an old refresh token now returns 401.

---

## 5. Datetime Normalization
File: `app/timeutils.py`

Bug:
Datetime timezone offsets were discarded instead of converted.

Why it was wrong:
All datetime values must be normalized to UTC before storage and comparison.

Fix:
Timezone-aware datetime inputs are now converted to UTC before internal storage.

---

## 6. Invalid Booking Window Validation
File: `app/routers/bookings.py`

Bug:
Invalid booking windows could pass validation:
- past start time had grace
- `end_time <= start_time` could pass
- zero duration could pass
- non-whole-hour duration could pass
- invalid duration range was not fully checked

Why it was wrong:
Booking duration must be a whole number of hours, minimum 1 hour and maximum 8 hours. Start time must be strictly in the future.

Fix:
Added strict validation for:
- `start_time > now`
- `end_time > start_time`
- whole-hour duration
- 1 to 8 hour duration

Expected invalid response:
- Status: 400
- Code: INVALID_BOOKING_WINDOW

---

## 7. Booking Conflict Logic
File: `app/routers/bookings.py`

Bug:
Back-to-back bookings were rejected as conflicts.

Why it was wrong:
Back-to-back bookings are allowed. Only real overlaps should conflict.

Fix:
Changed overlap check to strict overlap logic:

existing.start_time < new.end_time AND new.start_time < existing.end_time

Expected conflict response:
- Status: 409
- Code: ROOM_CONFLICT

---

## 8. Booking Quota
File: `app/routers/bookings.py`

Bug:
Quota enforcement was not protected well enough during booking creation.

Why it was wrong:
A member can have at most 3 confirmed bookings starting within the next 24 hours.

Fix:
Quota check now runs inside the protected booking creation section.

Expected quota response:
- Status: 409
- Code: QUOTA_EXCEEDED

---

## 9. Booking Visibility
File: `app/routers/bookings.py`

Bug:
A member could access another member's booking in the same organization.

Why it was wrong:
Members can only read/cancel their own bookings. Admins can access all bookings in their organization.

Fix:
Added member ownership check.

Expected unauthorized member response:
- Status: 404
- Code: BOOKING_NOT_FOUND

---

## 10. Booking Detail Start Time
File: `app/routers/bookings.py`

Bug:
`GET /bookings/{id}` returned `created_at` as `start_time`.

Why it was wrong:
The endpoint must return the actual booking start time.

Fix:
Removed the incorrect overwrite and used the booking serializer correctly.

---

## 11. Booking Pagination
File: `app/routers/bookings.py`

Bug:
Pagination used wrong ordering, wrong offset, and ignored requested limit.

Why it was wrong:
Bookings must be sorted by ascending `start_time`, tie-break by `id`, and offset must be `(page - 1) * limit`.

Fix:
Corrected ordering, offset, limit, and total count.

---

## 12. Refund Policy
Files:
- `app/routers/bookings.py`
- `app/services/refunds.py`

Bug:
Refund tier logic and rounding were wrong.

Why it was wrong:
Required policy:
- 48 hours or more: 100%
- 24 hours to less than 48 hours: 50%
- less than 24 hours: 0%

Half-cent values must round up.

Fix:
Corrected refund tier logic and used integer half-up cent rounding.

Verified example:
50% of 1001 cents = 501 cents.

---

## 13. Duplicate Cancellation
File: `app/routers/bookings.py`

Bug:
Concurrent or repeated cancellation could risk incorrect refund behavior.

Why it was wrong:
A booking should be cancelled only once and should have exactly one refund log.

Fix:
Cancellation now runs inside a protected critical section.

Expected duplicate cancellation response:
- Status: 409
- Code: ALREADY_CANCELLED

---

## 14. Rate Limit
File: `app/services/ratelimit.py`

Bug:
Rate-limit bucket state was not concurrency-safe.

Why it was wrong:
All booking attempts must count, including failed attempts, and the limit must hold under concurrent requests.

Fix:
Added locking around rolling-window rate-limit state.

Expected rate-limit response:
- Status: 429
- Code: RATE_LIMITED

---

## 15. Reference Code Uniqueness
File: `app/services/reference.py`

Bug:
Reference code generation used shared mutable state without synchronization.

Why it was wrong:
Concurrent booking creation could generate duplicate reference codes.

Fix:
Added locking around reference code generation.

---

## 16. Notification Side Effects
File: `app/services/notifications.py`

Bug:
Notification simulation had unnecessary delay/locking behavior.

Why it was risky:
It could slow down concurrent API requests and increase liveness risk.

Fix:
Simplified notification hooks to safe no-op functions.

---

## 17. Room Stats
File: `app/routers/rooms.py`

Bug:
Room stats depended on fragile in-memory state.

Why it was wrong:
Stats must reflect the current confirmed bookings in the database.

Fix:
Room stats are now computed directly from confirmed bookings in the database.

---

## 18. Availability Cache
File: `app/routers/bookings.py`

Bug:
Availability could become stale after booking creation or cancellation.

Why it was wrong:
Availability must reflect current confirmed bookings.

Fix:
Booking creation and cancellation now invalidate related availability cache entries.

---

## 19. Admin Export Scoping
File: `app/services/export.py`

Bug:
Admin export with `include_all` and `room_id` could bypass organization scoping.

Why it was wrong:
Admins must only export bookings from their own organization.

Fix:
Export query now always joins through `Room` and filters by organization.

---

## 20. Concurrency Safety
Files:
- `app/routers/bookings.py`
- `app/services/reference.py`
- `app/services/ratelimit.py`
- `app/services/stats.py`

Bug:
Critical shared operations were not safe under concurrent requests.

Fix:
Added locks around:
- booking conflict check and creation
- quota check
- cancellation and refund
- reference generation
- rate-limit bucket updates
- stats updates

---

## Verification Summary
Local black-box, corner-case, and concurrency tests were run after the fixes.

Results:
- Final local black-box retest: 64 PASS, 0 FAIL
- Deep corner and concurrency retest: 90 PASS, 0 FAIL

Detailed testing summary is available in `TESTS_RUN.md`.
