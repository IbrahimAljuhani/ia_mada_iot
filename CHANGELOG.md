# Changelog — ia_mada_iot

## [18.0.1.1.0] - 2026-03-17
### Added
- `neoleap_ip` field on `pos.payment.method` — each payment method stores its own NeoLeap device IP
- `action_test_neoleap_connection` button — tests TCP connection to NeoLeap on port 7000 directly from the payment method form
- Support for unlimited Mada terminals — create one payment method per device
- `MadaInterface.get_devices()` now reads payment methods from Odoo and registers one IoT device per configured terminal
- `MadaDriver` passes `neoleap_ip` from Odoo to WebSocket connection instead of hardcoded localhost

### Fixed
- `inherit_id` ref corrected to `point_of_sale.pos_payment_method_view_form` (was `view_pos_payment_method_form`)
- Removed `i18n/` folder — caused `AttributeError: 'NoneType' object has no attribute 'groups'` on Arabic locale
- `controllers/main.py` override fixes IoT Box saas~19.1 compatibility (`mac=None, auto=True` defaults)

### Changed
- Bilingual messages (Arabic/English) now handled directly in `payment_mada.js` via `_t(ar, en)` helper — no `.po` files needed

---

## [18.0.1.0.2] - 2026-03-15
### Added
- `controllers/main.py` — overrides `/iot/get_handlers` to fix 500 error with IoT Box saas~19.1
- `controllers/__init__.py`

### Changed
- Version bumped to 18.0.1.0.2
- `__init__.py` updated to import controllers

---

## [18.0.1.0.1] - 2026-03-15
### Added
- Bilingual support in `payment_mada.js` — Arabic for ar_* users, English for others
- `_t(ar, en)` helper replaces Odoo `_t()` translation system
- Bank decline (StatusCode 01) handled separately with specific message

### Fixed
- Removed dependency on `.po` translation files for JS messages

---

## [18.0.1.0.0] - 2026-03-15
### Added
- Initial release by Ibrahim Aljuhani (info@ia.sa)
- Full NeoLeap protocol: CHECK_STATUS → SALE → TERMINAL_RESPONSE
- StatusCode mapping: 00 approved / 01 bank decline / 11 customer cancel
- Manual payment fallback: cashier can enter approval code if terminal fails
- `MadaDriver`: WebSocket client on Raspberry Pi → ws://IP:7000
- `MadaInterface`: auto-registers mada devices on IoT Box startup
- `PaymentMada` JS: communicates with IoT device
- `PaymentScreen` patch: handles mada_iot terminal, cancel, and line deletion
- Safe import guard: `mada_handler.py` loads on Odoo server without crash
- 90-second timeout with descriptive error messages
