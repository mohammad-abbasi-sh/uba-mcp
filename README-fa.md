# uba-mcp 🌬️

mcp-name: io.github.mohammad-abbasi-sh/uba-mcp

سرور MCP غیررسمی و **فقط‌خواندنی** برای **[کیفیت هوای UBA](https://www.umweltbundesamt.de/en/data/air/air-data)** — API نسخهٔ ۴ داده‌های هوای آژانس فدرال محیط زیست آلمان (Umweltbundesamt): اندازه‌گیری‌های ساعتی از حدود ۴۰۰ ایستگاه آلمان (PM10، PM2.5، NO2، O3، SO2، CO، بنزن و…) از سال ۲۰۱۶، همراه با شاخص رسمی کیفیت هوا (LQI) از UBA. بدون کلید، بدون ورود.

> ساختهٔ محمد عباسی، بخشی از «کارخانهٔ MCP آلمان». وابسته به Umweltbundesamt نیست.

## برای ایجنت‌های هوش مصنوعی

به پیکربندی MCP کلاینت اضافه کنید (stdio):

```json
{
  "mcpServers": {
    "uba": {
      "command": "uvx",
      "args": ["uba-mcp==0.1.0"]
    }
  }
}
```

یا به‌صورت محلی اجرا کنید: `python -m uba_mcp.server` (نیازمند `mcp<2` و `httpx`).

## ابزارها

| ابزار | توضیح |
|------|-------|
| `uba_list_stations` | ایستگاه‌های اندازه‌گیری، قابل فیلتر بر اساس شهر، ایالت، نوع، منطقه یا نام |
| `uba_station_detail` | یک ایستگاه: آدرس، مختصات، نوع، بازهٔ داده‌ها، آلاینده‌های اخیر |
| `uba_current_air_quality` | آخرین مقادیر ساعتی + شاخص LQI در یک ایستگاه (کد، شناسه یا نام شهر) |
| `uba_measurements` | مقادیر ساعتی در یک بازه (حداکثر ۳۱ روز) + کمینه/بیشینه/میانگین و میانگین روزانه |
| `uba_list_components` | هر ۱۲ آلاینده: کد، نماد، واحد، نام |
| `uba_list_networks` | ۱۷ شبکهٔ اندازه‌گیری (۱۶ ایالت + UBA) |
| `uba_health` | بررسی دسترس‌پذیری (ok / blocked / error) — یک درخواست مؤدبانه |

نکته‌ها:
- ایستگاه‌ها با کد (`DEBE010` = برلین ودینگ)، شناسهٔ عددی یا نام شهر پیدا می‌شوند (اولین ایستگاه فعال آن شهر).
- `index` / `total_index` (۰ تا ۴) و برچسب‌ها مستقیم از API می‌آیند و از شاخص LQI بازبینی‌شدهٔ ۲۰۲۵ پیروی می‌کنند: بسیار خوب / خوب / متوسط / بد / بسیار بد.
- همهٔ زمان‌ها CET/CEST هستند، همان‌طور که API برمی‌گرداند. داده‌ها: UBA Air Data API v4 — بدون کلید، بدون ورود، فقط‌خواندنی.

## توسعه

```bash
python3 -m venv .venv && .venv/bin/pip install "mcp<2" httpx pytest
.venv/bin/pip install -e .
.venv/bin/python -m pytest tests/ -q
```

## لایسنس

MIT

---

Built by [Mohammad Abbasi](https://github.com/mohammad-abbasi-sh) — [Almanibama](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)
