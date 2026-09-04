# SMS Provider Integration Overview

Comprehensive overview of supported SMS gateway providers in **Usimamizi Wi-Fi**:

| Provider Code | Provider Name | Base Endpoint | Auth Method | Priority Failover Support |
| :--- | :--- | :--- | :--- | :--- |
| `beem` | Beem Africa | `https://api.beem.africa/v1/send-sms` | Basic Auth | Yes |
| `rafikisms` | RafikiSMS | `https://api.rafikisms.com/v1/vendor/send-sms` | `X-API-Key` | Yes |
| `nextsms` | NextSMS Tanzania | `https://messaging-service.co.tz/api/sms/v2/text/single` | Bearer Token | Yes |
| `mock` | Mock Provider | Local Memory / Logs | None | Yes |
