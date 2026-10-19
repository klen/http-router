# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [9.0.0] - 2026-10-19

### Changed

- Dropped Python 3.10 support; the minimum required version is now Python 3.11.

## [8.0.0] - 2026-10-19

### Added

- `hosts` parameter to restrict routes to specific host(s), compared verbatim.

## [7.1.1] - 2026-10-18

### Changed

- Typed `match()` locals and removed a redundant `cast()` in `Mount.match`.
- Documented ASGI usage and renamed the example variable from `app` to `router`.

## [7.1.0] - 2026-10-17

### Added

- Python 3.14 support.
- `unquote_params` option to skip unquoting captured path parameters (e.g. for ASGI).

### Removed

- Python 3.9 support.

### Fixed

- Infinite loop on an unclosed nested `{` in a path pattern.
- Mounted routers now honor `trim_last_slash`, root path and methods.
- Mounted routers fall through when the child router returns no match.
- Captured params are immutable and no longer shared across requests.
- Case-insensitive method matching and uppercase UUID support.
- Dynamic-route fallback on method mismatch.
- Routers are now copyable and picklable.
