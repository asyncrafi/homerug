{%- comment -%}
  ═══════════════════════════════════════════════════
  Rug Configurator — Single Page
  Updated: Direct checkout from configurator page
           No mat-room page needed
  FIXES APPLIED (latest round):
    1. Price only shows AFTER image generation (not on every input change)
       AND is now positioned BELOW the generated images, not in the form.
    2. 3x generation limit enforced (server + client)
    3. Login-free (guest) access confirmed intact
    4. Generation is async (Celery) — POST /generate/ returns "pending"
       immediately; frontend polls poll_url until "generated"/"failed".
    5. Shape dropdown (rectangular/round) added, sent to /generate/,
       populated from /options/ (falls back to a hardcoded list).
    6. Quantity stepper added, sent to /checkout/.
    7. Favorite/Save button added, calls /<generation_id>/favorite/.
    8. Mobile "Generating…" text now stays visible next to the spinner.
    9. Cotton and Jute removed from the material fallback list.
    10. Generated designs are now persisted to localStorage per customer
        email, so a refresh/accidental navigation restores the last
        generated set instead of losing it.
  ═══════════════════════════════════════════════════
{%- endcomment -%}

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&family=Lora:wght@400;600;700;800&display=swap" rel="stylesheet">

<style>
  .pmc-wrapper * { margin:0; padding:0; box-sizing:border-box; }
  .pmc-wrapper {
    --bg-deep: #ffffffff;
    --bg-card: rgba(255,255,255,0.025);
    --bg-input: rgba(255,255,255,0.04);
    --bg-input-focus: rgba(255,255,255,0.07);
    --border-subtle: rgba(255,255,255,0.06);
    --border-medium: rgba(255,255,255,0.1);
    --border-focus: rgba(16,185,129,0.4);
    --green: #10b981;
    --green-dark: #059669;
    --green-glow: rgba(16,185,129,0.25);
    --gold: #d4a843;
    --gold-glow: rgba(212,168,67,0.2);
    --text-primary: #f0f0f5;
    --text-secondary: #9090a8;
    --text-muted: #555568;
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
    --radius-xl: 20px;
    --shadow-card: 0 8px 40px rgba(0,0,0,0.4);
    --transition-fast: 0.2s cubic-bezier(0.4,0,0.2,1);
    --transition-medium: 0.35s cubic-bezier(0.4,0,0.2,1);
    font-family: 'Poppins', -apple-system, BlinkMacSystemFont, sans-serif;
    color: var(--text-primary);
    background: var(--bg-deep);
    min-height: 100vh;
    position: relative;
    overflow-x: hidden;
  }
  .pmc-wrapper::before {
    content: '';
    position: fixed;
    top:0; left:0; right:0; bottom:0;
    background:
      radial-gradient(circle at 15% 25%, rgba(16,185,129,0.04), transparent 50%),
      radial-gradient(circle at 85% 75%, rgba(212,168,67,0.03), transparent 50%);
    pointer-events: none;
    z-index: 0;
  }
  .pmc-content { position:relative; z-index:1; max-width:1280px; margin:0 auto; padding:40px 24px 60px; }

  /* Header */
  .pmc-header { text-align:center; margin-bottom:48px; animation:pmc-fadeInDown 0.6s ease-out; }
  .pmc-header__title {
    font-family:'Poppins',serif; font-size:clamp(28px,4vw,42px); font-weight:500;
    background:#000; -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    background-clip:text; margin-bottom:0px; line-height:60px;
  }
  .pmc-header__subtitle { font-size:16px; color:var(--text-secondary); font-weight:300; }
  .pmc-step-badge {
    display:inline-flex; align-items:center; gap:6px; margin-top:16px; padding:6px 16px;
    background:var(--bg-card); border:1px solid var(--border-subtle);
    border-radius:100px; font-size:12px; color:var(--text-secondary);
    letter-spacing:1px; text-transform:Normal;
  }
  .pmc-step-badge__dot { width:6px; height:6px; border-radius:50%; background:#033702; box-shadow:0 0 8px var(--green-glow); }

  /* Layout */
  .pmc-main { display:grid; grid-template-columns:420px 1fr; gap:32px; align-items:start; animation:pmc-fadeInUp 0.7s ease-out 0.15s both; }
  @media (max-width:900px) { .pmc-main { grid-template-columns:1fr; } }

  /* Cards */
  .pmc-form-card, .pmc-preview-card {
    background:var(--bg-card); border:1px solid var(--border-subtle);
    border-radius:var(--radius-xl); padding:32px;
    backdrop-filter:blur(20px); box-shadow:var(--shadow-card);
    transition:border-color var(--transition-medium);
  }
  .pmc-form-card:hover, .pmc-preview-card:hover { border-color:var(--border-medium); }
  .pmc-form-card__title { font-family:'Poppins',serif; font-size:20px; font-weight:600; margin-bottom:4px; }
  .pmc-form-card__desc { font-size:13px; color:var(--text-muted); margin-bottom:28px;  }

  /* Form */
  .pmc-form-group { margin-bottom:24px; }
  .pmc-label { display:block; font-size:12px; font-weight:600; color:#000; text-transform:uppercase; letter-spacing:1.2px; margin-bottom:10px; }
  .pmc-select-wrap { position:relative; }
  .pmc-select-wrap::after { content:'▾'; position:absolute; right:14px; top:50%; transform:translateY(-50%); color:#000; pointer-events:none; }
  .pmc-select {
    width:100%; padding:12px 36px 12px 14px;
    background:rgb(3 55 2 / 6%); border:1px solid var(--border-subtle);
    border-radius:var(--radius-md); color:#000;
    font-family:'Poppins',sans-serif; font-size:14px;
    appearance:none; -webkit-appearance:none; cursor:pointer;
    transition:all var(--transition-fast); outline:none;
  }
  .pmc-select:focus { border-color:var(--border-focus); }
  .pmc-input {
    width:100%; padding:12px 14px;
    background:rgb(3 55 2 / 6%); border:1px solid transparent;
    border-radius:var(--radius-md); color:#000;
    font-family:'Poppins',sans-serif; font-size:14px;
    transition:all var(--transition-fast); outline:none;
  }
  .pmc-input::placeholder { color:var(--text-muted); }
  .pmc-input:focus { border-color:var(--border-focus); box-shadow:0 0 0 3px rgba(16,185,129,0.1); }
  .pmc-input-hint { font-size:11px; color:var(--text-muted); margin-top:5px; }
  .pmc-input-hint.error { color:#f87171; }

  /* Color tags */
  .pmc-color-input-wrap {
    background:rgb(3 55 2 / 6%); border:1px solid var(--border-subtle);
    border-radius:var(--radius-md); padding:8px 10px;
    display:flex; flex-wrap:wrap; gap:6px; align-items:center;
    cursor:text; transition:all var(--transition-fast); min-height:46px;
  }
  .pmc-color-input-wrap:focus-within { border-color:var(--border-focus); box-shadow:0 0 0 3px rgba(16,185,129,0.1); }
  .pmc-color-tag {
    display:inline-flex; align-items:center; gap:5px; padding:4px 10px 4px 8px;
    background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.3);
    border-radius:100px; font-size:12px; color:#000; white-space:nowrap;
  }
  .pmc-color-tag__swatch { width:12px; height:12px; border-radius:50%; border:1px solid rgba(255,255,255,0.2); flex-shrink:0; }
  .pmc-color-tag__remove { background:none; border:none; color:#000; cursor:pointer; font-size:14px; line-height:1; padding:0; margin-left:2px; }
  .pmc-color-tag__remove:hover { color:#f87171; }
  .pmc-color-input { flex:1; min-width:120px; background:none; border:1px solid transparent; outline:none; color:#000; font-family:'Poppins',sans-serif; font-size:13px; padding:2px 4px; }
  .pmc-color-input::placeholder { color:var(--text-muted); }

  /* Textarea */
  .pmc-textarea {
    width:100%; min-height:80px; padding:12px 14px;
    background:rgb(3 55 2 / 6%); border:1px solid var(--border-subtle);
    border-radius:var(--radius-md); color:#000;
    font-family:'Poppins',sans-serif; font-size:14px;
    resize:vertical; transition:all var(--transition-fast); outline:none;
  }
  .pmc-textarea::placeholder { color:var(--text-muted); }
  .pmc-textarea:focus { border-color:var(--border-focus); box-shadow:0 0 0 3px rgba(16,185,129,0.1); }
  .pmc-char-count { text-align:right; font-size:11px; color:var(--text-muted); margin-top:4px; }

  /* Price box — now rendered in the PREVIEW card, below the images */
  .pmc-price-box {
    display:none; margin-top:20px; padding:16px 20px;
    background:linear-gradient(135deg,rgba(16,185,129,0.06),rgba(212,168,67,0.04));
    border:1px solid rgba(16,185,129,0.15); border-radius:var(--radius-md);
    width:100%;
  }
  .pmc-price-box.visible { display:block; }
  .pmc-price-box__label { font-size:11px; color:var(--text-muted); text-transform:uppercase; letter-spacing:1px; margin-bottom:4px; }
  .pmc-price-box__amount {
    font-family:'Lora',serif; font-size:32px; font-weight:700;
    background:linear-gradient(135deg,var(--green),var(--gold));
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
  }
  .pmc-price-box__breakdown { font-size:11px; color:var(--text-muted); margin-top:4px; }

  /* Generate button */
  .pmc-btn-generate {
    width:100%; margin-top:24px; padding:16px 24px; background:#033702;
    border:none; border-radius:var(--radius-md); color:#fff;
    font-family:'Poppins',sans-serif; font-size:15px; font-weight:600;
    cursor:pointer; transition:all var(--transition-medium); letter-spacing:0.3px;
  }
  .pmc-btn-generate:hover { transform:translateY(-2px); box-shadow:0 8px 32px var(--green-glow); }
  .pmc-btn-generate:disabled { opacity:0.5; cursor:not-allowed; transform:none; }
  .pmc-btn-generate__text { display:inline-flex; align-items:center; gap:8px; }
  .pmc-spinner { display:none; width:20px; height:20px; border:2px solid rgba(255,255,255,0.3); border-top-color:#fff; border-radius:50%; animation:pmc-spin 0.7s linear infinite; }
  .pmc-btn-generate.loading .pmc-spinner { display:inline-block; }
  /* NOTE: label text is intentionally kept visible while loading (mobile fix) —
     JS swaps the text itself to "Generating…" instead of hiding it. */

  /* Gen counter */
  .pmc-gen-counter { text-align:center; margin-top:10px; font-size:12px; color:var(--text-muted); }
  .pmc-gen-counter span { color:#033702; font-weight:600; }

  /* Preview panel */
  .pmc-preview-card { min-height:500px; display:flex; flex-direction:column; align-items:center; justify-content:center; position:relative; overflow:hidden; }
  .pmc-preview-empty { text-align:center; padding:40px 20px; }
  .pmc-preview-empty__icon { font-size:64px; margin-bottom:16px; opacity:0.4; }
  .pmc-preview-empty__title { font-family:'Lora',serif; font-size:18px; color:var(--text-secondary); margin-bottom:8px; }
  .pmc-preview-empty__text { font-size:13px; color:#033702; max-width:280px; margin:0 auto; line-height:1.5; }

  .pmc-preview-loading { display:none; text-align:center; width:100%; }
  .pmc-preview-loading.visible { display:block; }
  .pmc-preview-skeleton { width:100%; max-width:400px; aspect-ratio:2/3; margin:0 auto 20px; border-radius:var(--radius-lg); background:linear-gradient(110deg,var(--bg-input) 30%,rgba(255,255,255,0.06) 50%,var(--bg-input) 70%); background-size:200% 100%; animation:pmc-shimmer 1.5s ease-in-out infinite; }
  .pmc-preview-loading__text { font-size:14px; color:var(--text-secondary); animation:pmc-pulse 1.5s ease-in-out infinite; }
  .pmc-progress-bar { width:100%; max-width:300px; height:3px; background:var(--bg-input); border-radius:4px; margin:12px auto 0; overflow:hidden; }
  .pmc-progress-bar__fill { height:100%; width:0%; background:linear-gradient(90deg,var(--green),var(--gold)); border-radius:4px; transition:width 0.3s ease; }

  .pmc-images-grid-wrap { display:none; width:100%; animation:pmc-scaleIn 0.5s cubic-bezier(0.34,1.56,0.64,1); }
  .pmc-images-grid-wrap.visible { display:block; }
  .pmc-images-grid-title { font-family:'Lora',serif; font-size:15px; color:var(--text-secondary); text-align:center; margin-bottom:14px; }
  .pmc-images-grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
  .pmc-image-option { position:relative; cursor:pointer; border-radius:var(--radius-md); overflow:hidden; border:2px solid var(--border-subtle); transition:all var(--transition-medium); aspect-ratio:3/4; background:var(--bg-input); }
  .pmc-image-option:hover { border-color:rgba(16,185,129,0.4); transform:scale(1.02); box-shadow:0 8px 24px rgba(0,0,0,0.4); }
  .pmc-image-option.selected { border-color:var(--green); box-shadow:0 0 0 2px var(--green),0 0 24px var(--green-glow); }
  .pmc-image-option__img { width:100%; height:100%; object-fit:cover; display:block; transition:transform var(--transition-medium); }
  .pmc-image-option:hover .pmc-image-option__img { transform:scale(1.03); }
  .pmc-image-option__overlay { position:absolute; bottom:0; left:0; right:0; padding:10px; background:linear-gradient(to top,rgba(0,0,0,0.75) 0%,transparent 100%); display:flex; align-items:center; justify-content:space-between; }
  .pmc-image-option__num { font-size:11px; font-weight:600; color:rgba(255,255,255,0.7); letter-spacing:0.5px; text-transform:uppercase; }
  .pmc-image-option__check { display:none; background:var(--green); color:white; border-radius:50%; width:22px; height:22px; align-items:center; justify-content:center; font-size:12px; font-weight:700; }
  .pmc-image-option.selected .pmc-image-option__check { display:inline-flex; }
  /* Zoom button on each thumbnail */
  .pmc-image-option__zoom {
    position:absolute; top:8px; right:8px; z-index:2;
    width:32px; height:32px; border-radius:50%;
    background:rgba(0,0,0,0.55); border:1px solid rgba(255,255,255,0.25);
    color:#fff; display:flex; align-items:center; justify-content:center;
    font-size:15px; cursor:pointer; backdrop-filter:blur(4px);
    transition:all var(--transition-fast); opacity:0.85;
  }
  .pmc-image-option__zoom:hover { background:var(--green); transform:scale(1.1); opacity:1; }

  /* Lightbox overlay */
  .pmc-lightbox {
    display:none; position:fixed; top:0; left:0; right:0; bottom:0;
    z-index:9999; background:rgba(5,5,10,0.94); backdrop-filter:blur(12px);
    align-items:center; justify-content:center; flex-direction:column;
    padding:24px; animation:pmc-fadeIn 0.25s ease-out;
  }
  .pmc-lightbox.visible { display:flex; }
  .pmc-lightbox__stage { position:relative; max-width:90vw; max-height:80vh; display:flex; align-items:center; justify-content:center; }
  .pmc-lightbox__img {
    max-width:90vw; max-height:80vh; object-fit:contain;
    border-radius:var(--radius-md); box-shadow:0 20px 80px rgba(0,0,0,0.6);
    animation:pmc-scaleIn 0.3s cubic-bezier(0.34,1.56,0.64,1);
  }
  .pmc-lightbox__close {
    position:absolute; top:-44px; right:0; width:36px; height:36px;
    border-radius:50%; background:rgba(255,255,255,0.1); border:1px solid rgba(255,255,255,0.2);
    color:#fff; font-size:18px; cursor:pointer; display:flex; align-items:center; justify-content:center;
    transition:all var(--transition-fast);
  }
  .pmc-lightbox__close:hover { background:rgba(239,68,68,0.7); }
  .pmc-lightbox__nav {
    position:absolute; top:50%; transform:translateY(-50%);
    width:44px; height:44px; border-radius:50%;
    background:rgba(255,255,255,0.1); border:1px solid rgba(255,255,255,0.2);
    color:#fff; font-size:20px; cursor:pointer; display:flex; align-items:center; justify-content:center;
    transition:all var(--transition-fast);
  }
  .pmc-lightbox__nav:hover { background:var(--green); }
  .pmc-lightbox__nav--prev { left:-60px; }
  .pmc-lightbox__nav--next { right:-60px; }
  @media (max-width:700px) {
    .pmc-lightbox__nav--prev { left:8px; }
    .pmc-lightbox__nav--next { right:8px; }
    .pmc-lightbox__close { top:8px; right:8px; }
  }
  .pmc-lightbox__caption {
    margin-top:16px; font-size:13px; color:var(--text-secondary); text-align:center;
  }
  .pmc-lightbox__select-btn {
    margin-top:14px; padding:10px 24px; background:var(--green); border:none;
    border-radius:var(--radius-md); color:#fff; font-family:'Poppins',sans-serif;
    font-size:13px; font-weight:600; cursor:pointer; transition:all var(--transition-fast);
  }
  .pmc-lightbox__select-btn:hover { background:var(--green-dark); transform:translateY(-1px); }

  .pmc-images-select-hint { text-align:center; font-size:12px; color:var(--text-muted); margin-top:12px; padding:8px 12px; border:1px dashed var(--border-subtle); border-radius:var(--radius-sm); }
  .pmc-images-select-hint.selected-hint { border-color:rgba(16,185,129,0.3); color:var(--green); background:rgba(16,185,129,0.05); }

  /* Quantity stepper */
  .pmc-qty-row { display:flex; align-items:center; justify-content:space-between; margin-top:16px; margin-bottom:14px; }
  .pmc-qty-stepper { display:flex; align-items:center; gap:0; border:1px solid var(--border-medium); border-radius:var(--radius-md); overflow:hidden; }
  .pmc-qty-btn { width:34px; height:34px; background:rgb(3 55 2 / 6%); border:none; color:#000; font-size:16px; cursor:pointer; transition:background var(--transition-fast); }
  .pmc-qty-btn:hover { background:rgba(16,185,129,0.15); }
  .pmc-qty-input { width:44px; height:34px; border:none; border-left:1px solid var(--border-medium); border-right:1px solid var(--border-medium); text-align:center; font-family:'Poppins',sans-serif; font-size:14px; color:#000; background:transparent; }

  /* ✅ Order Now button */
  .pmc-btn-order-wrap { display:none; margin-top:20px; width:100%; }
  .pmc-btn-order-wrap.visible { display:block; animation:pmc-fadeInUp 0.4s ease-out; }
  .pmc-btn-order {
    width:100%; padding:16px 24px;
    background:linear-gradient(135deg,var(--green),var(--green-dark));
    border:none; border-radius:var(--radius-md); color:#fff;
    font-family:'Poppins',sans-serif; font-size:15px; font-weight:600;
    cursor:pointer; transition:all var(--transition-medium);
    display:inline-flex; align-items:center; justify-content:center; gap:8px;
    box-shadow:0 4px 20px var(--green-glow);
  }
  .pmc-btn-order:hover { transform:translateY(-2px); box-shadow:0 8px 32px var(--green-glow); }
  .pmc-btn-order:disabled { opacity:0.5; cursor:not-allowed; transform:none; }

  /* Favorite / Save button */
  .pmc-btn-favorite {
    width:100%; margin-top:10px; padding:12px 20px; background:transparent;
    border:1px solid var(--border-medium); border-radius:var(--radius-md); color:var(--text-primary);
    font-family:'Poppins',sans-serif; font-size:13px; font-weight:600; cursor:pointer;
    transition:all var(--transition-fast);
  }
  .pmc-btn-favorite:hover { border-color:var(--gold); }
  .pmc-btn-favorite.saved { border-color:var(--green); color:var(--green); }
  .pmc-btn-favorite:disabled { opacity:0.6; cursor:not-allowed; }

  /* ✅ Checkout loading overlay */
  .pmc-checkout-loading {
    display:none; position:fixed; top:0; left:0; right:0; bottom:0;
    z-index:9997; background:rgba(7,7,13,0.9); backdrop-filter:blur(10px);
    align-items:center; justify-content:center; flex-direction:column; gap:16px;
  }
  .pmc-checkout-loading.visible { display:flex; }
  .pmc-checkout-loading__spinner { width:48px; height:48px; border:3px solid rgba(255,255,255,0.2); border-top-color:var(--green); border-radius:50%; animation:pmc-spin 0.8s linear infinite; }
  .pmc-checkout-loading__text { font-size:16px; color:#fff; }

  /* API Error */
  .pmc-api-error { display:none; text-align:center; padding:20px; background:rgba(239,68,68,0.05); border:1px solid rgba(239,68,68,0.2); border-radius:var(--radius-md); margin-bottom:20px; }
  .pmc-api-error.visible { display:block; }
  .pmc-api-error p { font-size:13px; color:#f87171; line-height:1.5; }

  /* Generation limit overlay */
  .pmc-limit-overlay {
    display:none; position:fixed; top:0; left:0; right:0; bottom:0;
    z-index:9998; background:rgba(7,7,13,0.97); backdrop-filter:blur(20px);
    align-items:center; justify-content:center;
  }
  .pmc-limit-overlay.visible { display:flex; }
  .pmc-limit-box {
    text-align:center; max-width:480px; padding:48px 40px;
    background:var(--bg-card); border:1px solid rgba(212,168,67,0.2);
    border-radius:var(--radius-xl); box-shadow:0 0 80px rgba(212,168,67,0.08),0 24px 80px rgba(0,0,0,0.6);
    animation:pmc-scaleIn 0.5s cubic-bezier(0.34,1.56,0.64,1);
  }
  .pmc-limit-box__icon { font-size:56px; margin-bottom:20px; display:block; }
  .pmc-limit-box__title { font-family:'Lora',serif; font-size:26px; font-weight:700; color:#fff; margin-bottom:16px; }
  .pmc-limit-box__text { font-size:15px; color:#fff; line-height:1.7; margin-bottom:28px; }
  .pmc-limit-box__email {
    display:inline-flex; align-items:center; gap:8px; padding:14px 28px;
    background:linear-gradient(135deg,var(--gold),#b8902e);
    border:none; border-radius:var(--radius-md); color:#fff;
    font-family:'Poppins',sans-serif; font-size:14px; font-weight:600;
    text-decoration:none; box-shadow:0 4px 20px var(--gold-glow); transition:all var(--transition-medium);
  }
  .pmc-limit-box__email:hover { transform:translateY(-2px); box-shadow:0 8px 32px var(--gold-glow); }
  .pmc-limit-box__note { font-size:15px; color:#fff; margin-top:16px; }

  .pmc-limit-box__home {
  display:inline-flex; align-items:center; gap:8px;
  margin-top:30px; padding:10px 20px;
  background:transparent; border:1px solid rgba(255,255,255,0.3);
  border-radius:var(--radius-md); color:#fff;
  font-family:'Poppins',sans-serif; font-size:14px; font-weight:500;
  text-decoration:none; transition:all var(--transition-medium);
}
.pmc-limit-box__home:hover { background:rgba(255,255,255,0.08); border-color:rgba(255,255,255,0.5); }

  /* Toast */
  .pmc-toast { position:fixed; top:24px; right:24px; padding:14px 20px; background:#d4a556; border:1px solid var(--border-medium); border-radius:var(--radius-md); color:#fff; font-size:14px; z-index:9999; transform:translateX(120%); transition:transform var(--transition-medium); backdrop-filter:blur(20px); box-shadow:0 8px 32px rgba(0,0,0,0.5); max-width:360px; }
  .pmc-toast.visible { transform:translateX(0); }
  .pmc-toast.error { border-color:rgba(239,68,68,0.3); background:rgba(239,68,68,0.9); }
  .pmc-toast.success { border-color:rgba(16,185,129,0.3); background:#033702; }

  /* Animations */
  @keyframes pmc-fadeIn { from{opacity:0} to{opacity:1} }
  @keyframes pmc-fadeInDown { from{opacity:0;transform:translateY(-20px)} to{opacity:1;transform:translateY(0)} }
  @keyframes pmc-fadeInUp { from{opacity:0;transform:translateY(20px)} to{opacity:1;transform:translateY(0)} }
  @keyframes pmc-scaleIn { from{opacity:0;transform:scale(0.9)} to{opacity:1;transform:scale(1)} }
  @keyframes pmc-shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
  @keyframes pmc-pulse { 0%,100%{opacity:0.5} 50%{opacity:1} }
  @keyframes pmc-spin { to{transform:rotate(360deg)} }
  .pmc-quicklinks { display:flex; gap:12px; margin-bottom:20px; }
  .pmc-quicklink { flex:1; padding:10px 14px; background:transparent; border:1px solid var(--border-medium); border-radius:var(--radius-md); color:#000; font-family:'Poppins',sans-serif; font-size:12px; font-weight:600; cursor:pointer; transition:all var(--transition-fast); }
  .pmc-quicklink:hover { border-color:var(--green); color:var(--green); }

  .pmc-list-modal { display:none; position:fixed; inset:0; z-index:9999; background:rgba(5,5,10,0.9); backdrop-filter:blur(10px); align-items:center; justify-content:center; padding:24px; }
  .pmc-list-modal.visible { display:flex; }
  .pmc-list-modal__box { background:#111; border-radius:var(--radius-lg); padding:24px; max-width:480px; width:100%; max-height:70vh; overflow-y:auto; position:relative; }
  .pmc-list-modal__close { position:absolute; top:16px; right:16px; background:none; border:none; color:#fff; font-size:18px; cursor:pointer; }
  .pmc-list-modal__title { color:#fff; font-family:'Lora',serif; margin-bottom:16px; }
  .pmc-list-item { display:flex; gap:12px; align-items:center; padding:10px; border-radius:var(--radius-sm); cursor:pointer; transition:background 0.2s; }
  .pmc-list-item:hover { background:rgba(255,255,255,0.05); }
  .pmc-list-item--failed { opacity:0.45; cursor:not-allowed; }
  .pmc-list-item--failed:hover { background:none; }
  .pmc-list-item__thumb { width:48px; height:48px; object-fit:cover; border-radius:6px; }
  .pmc-list-item__thumb--empty { display:flex; align-items:center; justify-content:center; background:rgba(255,255,255,0.05); font-size:18px; }
  .pmc-list-item__meta { color:#fff; font-size:13px; }
  @media (max-width:900px) { .pmc-content{padding:24px 16px 40px} .pmc-form-card,.pmc-preview-card{padding:24px} }
  @media (max-width:480px) { .pmc-images-grid{gap:8px} .pmc-limit-box{padding:32px 24px;margin:0 16px} }
</style>

<!-- Generation limit overlay -->
<div class="pmc-limit-overlay" id="pmc-limit-overlay">
  <div class="pmc-limit-box">
    <span class="pmc-limit-box__icon">🙏</span>
    <h2 class="pmc-limit-box__title">We're Here to Help</h2>
    <p class="pmc-limit-box__text">
      We're sorry you're not completely happy with your designs.<br>
      Please email us and someone will help you further.
    </p>
    <a class="pmc-limit-box__email" href="mailto:customercare@maiahomes.com">
      ✉️ customercare@maiahomes.com
    </a>
    <p class="pmc-limit-box__note">Our team typically responds within 24 hours</p>
    <a href="https://maiahomes.com/" class="pmc-limit-box__home">← Back to Home</a>
  </div>
</div>

<!-- Checkout loading overlay -->
<div class="pmc-checkout-loading" id="pmc-checkout-loading">
  <div class="pmc-checkout-loading__spinner"></div>
  <p class="pmc-checkout-loading__text">Preparing your order...</p>
</div>
<!-- Lightbox for viewing generated designs full-size -->
<div class="pmc-lightbox" id="pmc-lightbox">
  <div class="pmc-lightbox__stage">
    <button class="pmc-lightbox__close" id="pmc-lightbox-close" type="button" aria-label="Close">✕</button>
    <button class="pmc-lightbox__nav pmc-lightbox__nav--prev" id="pmc-lightbox-prev" type="button" aria-label="Previous">‹</button>
    <img class="pmc-lightbox__img" id="pmc-lightbox-img" src="" alt="Design preview">
    <button class="pmc-lightbox__nav pmc-lightbox__nav--next" id="pmc-lightbox-next" type="button" aria-label="Next">›</button>
  </div>
  <p class="pmc-lightbox__caption" id="pmc-lightbox-caption">Option 1 of 4</p>
  <button class="pmc-lightbox__select-btn" id="pmc-lightbox-select" type="button">✓ Select This Design</button>
</div>

<!-- History / Favorites list modal -->
<div class="pmc-list-modal" id="pmc-list-modal">
  <div class="pmc-list-modal__box">
    <button class="pmc-list-modal__close" id="pmc-list-modal-close">✕</button>
    <h3 class="pmc-list-modal__title" id="pmc-list-modal-title">History</h3>
    <div class="pmc-list-modal__items" id="pmc-list-modal-items"></div>
  </div>
</div>
<div class="pmc-wrapper" id="pmc-configurator">
  <div class="pmc-content">

    <header class="pmc-header">
      <h1 class="pmc-header__title">{{ section.settings.heading | default: 'Rug Configurator' }}</h1>
      <p class="pmc-header__subtitle">{{ section.settings.subheading | default: 'Design Your Perfect Custom Rug' }}</p>
      <div class="pmc-step-badge">

        We take pride in creating a masterpiece for you. Each piece is custom made specifically for you.<br> Actual colors may vary slightly due to screen display differences.
      </div>
    </header>

    <div class="pmc-main">

      <!-- Left: Form -->
      <div class="pmc-form-card">
        <h2 class="pmc-form-card__title" style="color:#000;">Design Options</h2>
        <p class="pmc-form-card__desc">Configure every detail of your rug</p>

        <div class="pmc-api-error" id="pmc-api-error">
          <p>⚠️ Could not load options. Please refresh the page.</p>
        </div>

        <div id="pmc-form-inner">
          <div class="pmc-form-group">
            <label class="pmc-label" for="pmc-style">Style</label>
            <div class="pmc-select-wrap">
              <select class="pmc-select" id="pmc-style"></select>
            </div>
          </div>

          <div class="pmc-form-group">
            <label class="pmc-label" for="pmc-material">Material</label>
            <div class="pmc-select-wrap">
              <select class="pmc-select" id="pmc-material"></select>
            </div>
          </div>

          <div class="pmc-form-group">
            <label class="pmc-label" for="pmc-shape">Shape</label>
            <div class="pmc-select-wrap">
              <select class="pmc-select" id="pmc-shape"></select>
            </div>
          </div>

          <div class="pmc-form-group">
            <label class="pmc-label">Size</label>
            <input type="text" class="pmc-input" id="pmc-size" placeholder="e.g. 5x8 feet  or  150x240 cm" autocomplete="off">
            <p class="pmc-input-hint" id="pmc-size-hint">Minimum 2x2 ft (61x61 cm). Enter in feet or cm.</p>
          </div>

          <div class="pmc-form-group">
            <label class="pmc-label">Colors</label>
            <div class="pmc-color-input-wrap" id="pmc-color-input-wrap">
              <input type="text" class="pmc-color-input" id="pmc-color-input" placeholder="Type a color and press Enter…" autocomplete="off">
            </div>
            <p class="pmc-input-hint">Press <strong>Enter</strong> or <strong>comma</strong> to add each color.</p>
          </div>

          <div class="pmc-form-group">
            <label class="pmc-label" for="pmc-description">Custom Description</label>
            <textarea class="pmc-textarea" id="pmc-description" placeholder="e.g. Medallion pattern with floral border, geometric accents..." maxlength="500"></textarea>
            <div class="pmc-char-count"><span id="pmc-char-count">0</span>/500</div>
          </div>
        </div>

        <div class="pmc-quicklinks" id="pmc-quicklinks">
          <button type="button" class="pmc-quicklink" id="pmc-link-history">View History</button>
          <button type="button" class="pmc-quicklink" id="pmc-link-favorites">Saved Designs</button>
        </div>

        <button class="pmc-btn-generate" id="pmc-btn-generate" type="button">
          <span class="pmc-btn-generate__text">
            <span class="pmc-btn-text-label">✨ Generate Designs</span>
            <span class="pmc-spinner"></span>
          </span>
        </button>
        <div class="pmc-gen-counter" id="pmc-gen-counter"></div>
      </div>

      <!-- Right: Preview -->
      <div class="pmc-preview-card" id="pmc-preview-card">
        <div class="pmc-preview-empty" id="pmc-preview-empty">
          <span class="pmc-preview-empty__icon">🎨</span>
          <h3 class="pmc-preview-empty__title">Your Rug Designs</h3>
          <p class="pmc-preview-empty__text">Configure your options and click <strong>"Generate Designs"</strong> to see four unique AI-generated rugs.</p>
        </div>

        <div class="pmc-preview-loading" id="pmc-preview-loading">
          <div class="pmc-preview-skeleton"></div>
          <p class="pmc-preview-loading__text" id="pmc-loading-text">Generating your rug designs...</p>
          <div class="pmc-progress-bar"><div class="pmc-progress-bar__fill" id="pmc-progress-fill"></div></div>
        </div>

        <div class="pmc-images-grid-wrap" id="pmc-images-grid-wrap">
          <p class="pmc-images-grid-title">Choose your favourite design</p>
          <div class="pmc-images-grid" id="pmc-images-grid"></div>
          <p class="pmc-images-select-hint" id="pmc-select-hint">👆 Click on a design to select it</p>

          <!-- Price now shows here, AFTER the generated designs, never before -->
          <div class="pmc-price-box" id="pmc-price-box">
            <div class="pmc-price-box__label">Estimated Price (per rug)</div>
            <div class="pmc-price-box__amount" id="pmc-price-amount">—</div>
            <div class="pmc-price-box__breakdown" id="pmc-price-breakdown" style="display:none;"></div>
          </div>

          <!-- ✅ Order Now button — replaces "Place in Room" -->
          <div class="pmc-btn-order-wrap" id="pmc-btn-order-wrap">
            <div class="pmc-qty-row" id="pmc-qty-row">
              <label class="pmc-label" style="margin-bottom:0;">Quantity</label>
              <div class="pmc-qty-stepper">
                <button type="button" class="pmc-qty-btn" id="pmc-qty-minus">−</button>
                <input type="number" id="pmc-qty-input" class="pmc-qty-input" value="1" min="1" max="20">
                <button type="button" class="pmc-qty-btn" id="pmc-qty-plus">+</button>
              </div>
            </div>
            <button class="pmc-btn-order" id="pmc-btn-order" type="button">
              🛒 Order Now — $<span id="pmc-order-price">—</span>
            </button>
            <button class="pmc-btn-favorite" id="pmc-btn-favorite" type="button">🤍 Save This Design</button>
            <p style="text-align:center; font-size:14px; color:#555568; margin-top:10px; line-height:1.6;">
             Please allow 6–8 weeks for standard delivery. For knotted rugs and oversized rugs, please allow 8–16 weeks for delivery.
            </p>
          </div>
        </div>
      </div>

    </div>

    <!-- Footer pagination dot removed — it served no purpose with a single dot -->

  </div>
</div>

<div class="pmc-toast" id="pmc-toast"></div>

<script>
(function() {
  'use strict';

  const API_BASE       = 'https://api.personalizerug.com';
  const CUSTOMER_EMAIL = {{ customer.email | json }};
  const API_HEADERS    = { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' };
  let MAX_GENS          = 5; // ← changed from const to let

  // ✅ Unlimited generation whitelist — bypasses gen limit for these emails
  const UNLIMITED_EMAILS = ['sivmey.hok@gmail.com', 'info@maiahomes.com'];
  const isUnlimitedUser = CUSTOMER_EMAIL && UNLIMITED_EMAILS.includes(CUSTOMER_EMAIL.toLowerCase().trim());
  if (isUnlimitedUser) MAX_GENS = Infinity;

  /* Polling config for async (Celery) generation */
  const POLL_INTERVAL_MS = 10000;
  const POLL_TIMEOUT_MS  = 600000;

  /* localStorage key for persisting the last generated set per customer,
     so an accidental refresh/navigation doesn't lose the 4 images. */
  const STORAGE_KEY = 'pmc_rug_state_' + (CUSTOMER_EMAIL || 'guest');
  const STORAGE_MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000; // 7 days

  /* Color hex map */
  const COLOR_HEX = {
    'navy blue':'#1a2f6e','cream':'#f5f0e1','terracotta':'#c4622d',
    'forest green':'#1e6e2e','burgundy':'#800020','charcoal':'#36454f',
    'ivory':'#fffef0','rust':'#b7410e','sage green':'#7a9e7e',
    'camel':'#c19a6b','black':'#1a1a1a','gold':'#d4a843',
    'red':'#cc2200','blue':'#1e40af','grey':'#6b7280','gray':'#6b7280',
    'brown':'#7c4a1e','beige':'#d9c8a0','white':'#f5f5f5',
    'pink':'#d4748a','purple':'#6b3fa0','orange':'#d97706',
    'teal':'#0f766e','olive':'#5d6c1e','silver':'#a8a8b8',
  };
  function getHex(name) {
    const k = name.toLowerCase().trim();
    if (COLOR_HEX[k]) return COLOR_HEX[k];
    for (const [key, val] of Object.entries(COLOR_HEX)) {
      if (k.includes(key) || key.includes(k)) return val;
    }
    return '#888';
  }

  /* Pricing (local fallback only — server pricing is preferred when present) */
  const PREMIUM = ['new zealand wool','silk'];
  function parseSqft(sizeStr, shape) {
    const s = (sizeStr || '').toLowerCase().trim();
    const isCm = s.includes('cm');
    const nums = s.match(/[\d]+(?:\.[\d]+)?/g);
    if (!nums || nums.length === 0) return null;

    if (shape === 'round') {
      if (nums.length !== 1) return null;
      const diameter = parseFloat(nums[0]);
      const diameterFt = isCm ? diameter / 30.48 : diameter;
      const radiusFt = diameterFt / 2;
      return Math.PI * radiusFt * radiusFt;
    }

    if (nums.length < 2) return null;
    let d1 = parseFloat(nums[0]), d2 = parseFloat(nums[1]);
    if (isCm) { d1 /= 30.48; d2 /= 30.48; }
    return d1 * d2;
  }
  function validateSize(sizeStr, shape) {
    const s = (sizeStr || '').toLowerCase().trim();
    const isCm = s.includes('cm');
    const nums = s.match(/[\d]+(?:\.[\d]+)?/g);

    if (!nums || nums.length === 0) {
      return shape === 'round'
        ? 'Enter a diameter like "6 feet" or "180 cm".'
        : 'Enter size like "5x8 feet" or "150x240 cm"';
    }

    if (shape === 'round') {
      if (nums.length !== 1) return 'For round rugs, enter one diameter like "6 feet" or "180 cm".';
      const diameter = parseFloat(nums[0]);
      const minDim = isCm ? 61 : 2;
      if (diameter < minDim) return `Minimum diameter is 2 ft (61 cm). Got ${diameter} ${isCm?'cm':'ft'}.`;
      return null;
    }

    if (nums.length < 2) return 'Enter size like "5x8 feet" or "150x240 cm"';
    const d1 = parseFloat(nums[0]), d2 = parseFloat(nums[1]);
    const minDim = isCm ? 61 : 2;
    if (d1 < minDim || d2 < minDim) return `Minimum size is 2x2 ft (61x61 cm). Got ${d1}x${d2} ${isCm?'cm':'ft'}.`;
    return null;
  }
  function roundToX9(price) {
    const floored = Math.floor(price);
    const base = floored - (floored % 10);
    let candidate = base + 9;
    if (candidate < price) candidate += 10;
    return candidate;
  }
  function calcPrice(sizeStr, material, shape) {
    const sqft = parseSqft(sizeStr, shape);
    if (!sqft || sqft <= 0) return null;
    const isPremium = PREMIUM.includes((material||'').toLowerCase().trim());
    const rate = isPremium ? 49 : 39;
    const raw = sqft * rate;
    const price = roundToX9(raw);
    return { sqft: sqft.toFixed(1), rate, price, isPremium };
  }

  /* DOM */
  const dom = {
    limitOverlay:    document.getElementById('pmc-limit-overlay'),
    checkoutLoading: document.getElementById('pmc-checkout-loading'),
    apiError:        document.getElementById('pmc-api-error'),
    styleSelect:     document.getElementById('pmc-style'),
    materialSelect:  document.getElementById('pmc-material'),
    shapeSelect:     document.getElementById('pmc-shape'),
    sizeInput:       document.getElementById('pmc-size'),
    sizeHint:        document.getElementById('pmc-size-hint'),
    colorWrap:       document.getElementById('pmc-color-input-wrap'),
    colorInput:      document.getElementById('pmc-color-input'),
    description:     document.getElementById('pmc-description'),
    charCount:       document.getElementById('pmc-char-count'),
    priceBox:        document.getElementById('pmc-price-box'),
    priceAmount:     document.getElementById('pmc-price-amount'),
    priceBreakdown:  document.getElementById('pmc-price-breakdown'),
    btnGenerate:     document.getElementById('pmc-btn-generate'),
    btnGenerateLabel:document.querySelector('#pmc-btn-generate .pmc-btn-text-label'),
    genCounter:      document.getElementById('pmc-gen-counter'),
    previewEmpty:    document.getElementById('pmc-preview-empty'),
    previewLoading:  document.getElementById('pmc-preview-loading'),
    progressFill:    document.getElementById('pmc-progress-fill'),
    loadingText:     document.getElementById('pmc-loading-text'),
    imagesGridWrap:  document.getElementById('pmc-images-grid-wrap'),
    imagesGrid:      document.getElementById('pmc-images-grid'),
    selectHint:      document.getElementById('pmc-select-hint'),
    btnOrderWrap:    document.getElementById('pmc-btn-order-wrap'),
    btnOrder:        document.getElementById('pmc-btn-order'),
    orderPrice:      document.getElementById('pmc-order-price'),
    qtyInput:        document.getElementById('pmc-qty-input'),
    qtyMinus:        document.getElementById('pmc-qty-minus'),
    qtyPlus:         document.getElementById('pmc-qty-plus'),
    btnFavorite:     document.getElementById('pmc-btn-favorite'),
    toast:           document.getElementById('pmc-toast'),
    lightbox:        document.getElementById('pmc-lightbox'),
    lightboxImg:      document.getElementById('pmc-lightbox-img'),
    lightboxCaption:  document.getElementById('pmc-lightbox-caption'),
    lightboxClose:    document.getElementById('pmc-lightbox-close'),
    lightboxPrev:     document.getElementById('pmc-lightbox-prev'),
    lightboxNext:     document.getElementById('pmc-lightbox-next'),
    lightboxSelectBtn:document.getElementById('pmc-lightbox-select'),
    linkHistory:      document.getElementById('pmc-link-history'),
    linkFavorites:    document.getElementById('pmc-link-favorites'),
    listModal:        document.getElementById('pmc-list-modal'),
    listModalTitle:   document.getElementById('pmc-list-modal-title'),
    listModalItems:   document.getElementById('pmc-list-modal-items'),
    listModalClose:   document.getElementById('pmc-list-modal-close'),
  };

  /* State */
  const state = {
    style:'', material:'', shape:'rectangular', size:'', colors:[],
    description:'', generationId:null, generatedImages:[],
    selectedIndex:null, isGenerating:false,
    gensUsed:0, gensRemaining:MAX_GENS,
    currentPrice:null, currentPricing:null, quantity:1, isFavorited:false,
  };

  function updateOrderTotal() {
    if (state.currentPrice == null) return;
    dom.orderPrice.textContent = (state.currentPrice * state.quantity).toFixed(0);
  }

  /* ── localStorage persistence (fixes: "preserve images on refresh") ── */
  function saveToStorage() {
    try {
      if (!state.generationId || !state.generatedImages.length) return;
      const payload = {
        generationId: state.generationId,
        images: state.generatedImages,
        pricing: state.currentPricing,
        style: state.style, material: state.material, shape: state.shape,
        size: state.size, colors: state.colors, description: state.description,
        selectedIndex: state.selectedIndex, quantity: state.quantity,
        isFavorited: state.isFavorited,
        savedAt: Date.now(),
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
    } catch (e) { /* storage unavailable — non-fatal, just skip persistence */ }
  }

  function clearStorage() {
    try { localStorage.removeItem(STORAGE_KEY); } catch (e) {}
  }

  function restoreFromStorage() {
    let saved;
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      saved = JSON.parse(raw);
    } catch (e) { return; }
    if (!saved || !saved.generationId || !saved.images || !saved.images.length) return;
    if (Date.now() - (saved.savedAt || 0) > STORAGE_MAX_AGE_MS) { clearStorage(); return; }

    // Repopulate the form so it matches what was generated
    if (saved.style && dom.styleSelect.querySelector(`option[value="${CSS.escape(saved.style)}"]`)) {
      dom.styleSelect.value = saved.style;
    }
    if (saved.material && dom.materialSelect.querySelector(`option[value="${CSS.escape(saved.material)}"]`)) {
      dom.materialSelect.value = saved.material;
    }
    if (saved.shape && dom.shapeSelect.querySelector(`option[value="${CSS.escape(saved.shape)}"]`)) {
      dom.shapeSelect.value = saved.shape;
    }
    state.style = dom.styleSelect.value;
    state.material = dom.materialSelect.value;
    state.shape = dom.shapeSelect.value;

    if (saved.size) { dom.sizeInput.value = saved.size; state.size = saved.size; }
    if (Array.isArray(saved.colors)) { state.colors = saved.colors; renderColorTags(); }
    if (saved.description) { dom.description.value = saved.description; state.description = saved.description; dom.charCount.textContent = saved.description.length; }

    state.generationId = saved.generationId;
    state.quantity = saved.quantity || 1;
    dom.qtyInput.value = state.quantity;
    state.isFavorited = !!saved.isFavorited;

    dom.previewEmpty.style.display = 'none';
    showImagesGrid(saved.images, saved.generationId);

    if (saved.pricing) {
      applyServerPricing(saved.pricing);
    }

    if (typeof saved.selectedIndex === 'number') {
      selectImage(saved.selectedIndex);
    }

    if (state.isFavorited) {
      dom.btnFavorite.textContent = '❤️ Saved';
      dom.btnFavorite.classList.add('saved');
    }

    showToast('Restored your last generated designs.', 'success');
  }

  /* Init */
  async function init() {
    // ✅ Login required — generation limit is tracked per customer email,
    // so guests without login could bypass the 3x limit. Enforcing login here.
    if (!CUSTOMER_EMAIL) {
      window.location.href = '/account/login?return_url=/pages/bespoke-rugs-by-ai';
      return;
    }

    try {
      const res = await fetch(API_BASE + '/api/ruggen/options/?email=' + encodeURIComponent(CUSTOMER_EMAIL), { headers: { 'ngrok-skip-browser-warning': 'true' } });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const data = await res.json();

      const styles = data.styles || ['Persian','Moroccan','Traditional','Modern'];
      dom.styleSelect.innerHTML = styles.map(s => `<option value="${s}">${s}</option>`).join('');
      state.style = styles[0];

      // Cotton and Jute intentionally excluded — not offered anymore.
      const materials = (data.materials || ['New Zealand Wool','Silk','Wool','Synthetic'])
        .filter(m => !/cotton|jute/i.test(m));
      dom.materialSelect.innerHTML = materials.map(m => `<option value="${m}">${m}</option>`).join('');
      state.material = materials[0];

      const shapes = data.shapes || ['rectangular','round'];
      dom.shapeSelect.innerHTML = shapes.map(s => `<option value="${s}">${s.charAt(0).toUpperCase()+s.slice(1)}</option>`).join('');
      state.shape = shapes[0];

      state.gensUsed = data.generations_used || 0;
      state.gensRemaining = data.generations_remaining !== undefined ? data.generations_remaining : MAX_GENS;

    } catch(err) {
      console.error('Options fetch failed:', err);
      dom.apiError.classList.add('visible');
      ['Persian','Moroccan','Traditional','Modern','Geometric','Bohemian'].forEach(s => {
        dom.styleSelect.innerHTML += `<option value="${s}">${s}</option>`;
      });
      // Cotton and Jute removed from the fallback list too.
      ['New Zealand Wool','Silk','Wool','Synthetic','Bamboo'].forEach(m => {
        dom.materialSelect.innerHTML += `<option value="${m}">${m}</option>`;
      });
      dom.shapeSelect.innerHTML = `<option value="rectangular">Rectangular</option><option value="round">Round</option>`;
      state.style = 'Persian';
      state.material = 'New Zealand Wool';
      state.shape = 'rectangular';
    }

    updateGenCounter();

    // ✅ 3x generation limit — now ACTIVE
    if (state.gensUsed >= MAX_GENS) { showLimitScreen(); return; }

    attachListeners();
    restoreFromStorage();
  }

  /* Listeners */
  function attachListeners() {
    dom.styleSelect.addEventListener('change', function() { state.style = this.value; });
    dom.materialSelect.addEventListener('change', function() { state.material = this.value; });
    dom.shapeSelect.addEventListener('change', function() {
      state.shape = this.value;
      if (state.shape === 'round') {
        dom.sizeInput.placeholder = 'e.g. 6 feet (diameter)  or  180 cm';
        dom.sizeHint.textContent = 'For round rugs, enter the diameter, e.g. "6 feet" or "180 cm".';
      } else {
        dom.sizeInput.placeholder = 'e.g. 5x8 feet  or  150x240 cm';
        dom.sizeHint.textContent = 'Minimum 2x2 ft (61x61 cm). Enter in feet or cm.';
      }
      dom.sizeHint.classList.remove('error');
      dom.sizeHint.style.color = '';
    });
    // NOTE: no live price preview on material/size change — price only shows after Generate,
    // and only inside the preview card below the images.
    dom.sizeInput.addEventListener('input', function() {
      state.size = this.value.trim();
      if (state.size.length > 0) {
        const err = validateSize(state.size, state.shape);
        if (err) { dom.sizeHint.textContent = '⚠ ' + err; dom.sizeHint.classList.add('error'); dom.sizeHint.style.color = ''; }
        else { dom.sizeHint.textContent = state.shape === 'round' ? 'Looks good ✓' : 'Looks good ✓'; dom.sizeHint.classList.remove('error'); dom.sizeHint.style.color = 'var(--green)'; }
      }
    });
    dom.colorInput.addEventListener('keydown', function(e) {
      if (e.key==='Enter'||e.key===',') { e.preventDefault(); addColorTag(this.value); this.value=''; }
      else if (e.key==='Backspace'&&this.value===''&&state.colors.length>0) removeColorTag(state.colors.length-1);
    });
    dom.colorInput.addEventListener('blur', function() { if (this.value.trim()) { addColorTag(this.value); this.value=''; } });
    dom.colorWrap.addEventListener('click', () => dom.colorInput.focus());
    dom.description.addEventListener('input', function() { state.description=this.value; dom.charCount.textContent=this.value.length; });
    dom.btnGenerate.addEventListener('click', handleGenerate);
    dom.btnOrder.addEventListener('click', handleOrder);  // ✅ Order Now
    dom.btnFavorite.addEventListener('click', handleFavorite);

    dom.qtyMinus.addEventListener('click', () => setQuantity(state.quantity - 1));
    dom.qtyPlus.addEventListener('click', () => setQuantity(state.quantity + 1));
    dom.qtyInput.addEventListener('change', function() { setQuantity(parseInt(this.value) || 1); });

    dom.linkHistory.addEventListener('click', () => openListModal('history'));
    dom.linkFavorites.addEventListener('click', () => openListModal('favorites'));
    dom.listModalClose.addEventListener('click', closeListModal);
    dom.listModal.addEventListener('click', e => { if (e.target === dom.listModal) closeListModal(); });
  }
  function setQuantity(n) {
    state.quantity = Math.max(1, Math.min(20, n));
    dom.qtyInput.value = state.quantity;
    updateOrderTotal();
    saveToStorage();
  }

  /* Color tags */
  function addColorTag(raw) {
    const color = raw.replace(',','').trim().toLowerCase();
    if (!color) return;
    if (state.colors.includes(color)) { showToast('Color already added.', 'error'); return; }
    state.colors.push(color);
    renderColorTags();
  }
  function removeColorTag(index) { state.colors.splice(index,1); renderColorTags(); }
  function renderColorTags() {
    dom.colorWrap.querySelectorAll('.pmc-color-tag').forEach(t => t.remove());
    state.colors.forEach((color,i) => {
      const tag = document.createElement('span');
      tag.className = 'pmc-color-tag';
      tag.innerHTML = `<span class="pmc-color-tag__swatch" style="background:${getHex(color)}"></span>${color}<button type="button" class="pmc-color-tag__remove" data-index="${i}">×</button>`;
      tag.querySelector('.pmc-color-tag__remove').addEventListener('click', () => removeColorTag(i));
      dom.colorWrap.insertBefore(tag, dom.colorInput);
    });
  }

  /* Price display — local fallback only, used if server ever omits pricing */
  function displayPrice(sizeStr, material, shape) {
    const err = validateSize(sizeStr, shape || state.shape);
    if (err) { dom.priceBox.classList.remove('visible'); return; }
    const p = calcPrice(sizeStr, material||'Wool', shape || state.shape);
    if (!p) { dom.priceBox.classList.remove('visible'); return; }
    state.currentPrice = p.price;
    dom.priceAmount.textContent = '$' + p.price;
    dom.priceBreakdown.textContent = `${p.sqft} sqft × $${p.rate}/sqft${p.isPremium?' (premium material)':''}`;
    dom.priceBox.classList.add('visible');
    updateOrderTotal();
  }

  /* Apply pricing object as returned by the server (initial POST response) */
  function applyServerPricing(pricing) {
    if (!pricing) return;
    state.currentPrice = pricing.price;
    state.currentPricing = pricing;
    dom.priceAmount.textContent = '$' + pricing.price;
    dom.priceBreakdown.textContent = `${pricing.sqft} sqft × $${pricing.rate}/sqft${pricing.is_premium ? ' (premium material)' : ''}`;
    dom.priceBox.classList.add('visible');
    updateOrderTotal();
  }

  /* Gen counter */
  function updateGenCounter() {
    dom.genCounter.innerHTML = `Not sure if it's the perfect fit? <a href="mailto:customercare@maiahomes.com" style="color:#033702;font-weight:600;">Contact one of our stylists</a> for design tips and more!`;
  }

  /* Limit screen */
  function showLimitScreen() {
    dom.limitOverlay.classList.add('visible');
    dom.btnGenerate.disabled = true;
  }

  /* ─────────────────────────────────────────────────────────
     Async generation: POST kicks off a Celery job and returns
     immediately with status "pending" + a poll_url. We poll
     that URL until status flips to "generated" or "failed".
     ───────────────────────────────────────────────────────── */
async function pollGeneration(pollUrl, { intervalMs = POLL_INTERVAL_MS, timeoutMs = POLL_TIMEOUT_MS } = {}) {
    const start = Date.now();
    const url = pollUrl.startsWith('http') ? pollUrl : (API_BASE + pollUrl);

    // Fixed-interval polling: wait, then check, then wait again.
    // A bad HTTP response (429, network blip, 5xx, etc.) is NOT fatal —
    // we just skip that attempt and try again on the next tick.
    // Loop only ends when: image is ready, backend says "failed",
    // or we hit the overall timeout.
    while (Date.now() - start < timeoutMs) {
      await sleep(intervalMs); // wait ~10s between checks

      let res;
      try {
        res = await fetch(url, { headers: { 'ngrok-skip-browser-warning': 'true' } });
      } catch (networkErr) {
        continue; // couldn't reach server this time — retry next tick
      }

      if (!res.ok) {
        continue; // e.g. 429 or 5xx — don't fail, just retry next tick
      }

      let data;
      try {
        data = await res.json();
      } catch (parseErr) {
        continue; // bad/empty body — retry next tick
      }

      if (data.status === 'generated') return data;
      if (data.status === 'failed') throw new Error(data.error_message || data.error || 'Generation failed');

      // still "pending" — loop continues
    }
    throw new Error('Generation timed out — please try again.');
  }

  /* Generate */
  async function handleGenerate() {
    if (state.isGenerating) return;

    // ✅ 3x generation limit — now ACTIVE
    if (state.gensUsed >= MAX_GENS) { showLimitScreen(); return; }

    if (!state.style) { showToast('Please select a style.', 'error'); return; }
    if (!state.material) { showToast('Please select a material.', 'error'); return; }
    if (!state.size.trim()) { showToast('Please enter a size.', 'error'); return; }
    const sizeErr = validateSize(state.size, state.shape);
    if (sizeErr) { showToast(sizeErr, 'error'); return; }
    if (state.colors.length===0) { showToast('Please add at least one color.', 'error'); return; }

    state.isGenerating = true;
    state.selectedIndex = null;
    state.isFavorited = false;
    state.quantity = 1;
    dom.qtyInput.value = 1;
    dom.btnFavorite.textContent = '🤍 Save This Design';
    dom.btnFavorite.classList.remove('saved');
    clearStorage(); // a fresh generation replaces whatever was saved

    dom.btnGenerate.classList.add('loading');
    dom.btnGenerate.disabled = true;
    if (dom.btnGenerateLabel) dom.btnGenerateLabel.textContent = 'Generating…';
    dom.previewEmpty.style.display = 'none';
    dom.imagesGridWrap.classList.remove('visible');
    dom.btnOrderWrap.classList.remove('visible');
    dom.priceBox.classList.remove('visible'); // hide any stale price while regenerating
    dom.previewLoading.classList.add('visible');
    dom.progressFill.style.width = '0%';

    // Loading message rotator — keeps cycling for the whole poll duration,
    // not tied to a fixed timer anymore since generation time can vary.
    const messages = ['Analyzing your design preferences...','Crafting unique patterns...','Applying colors and textures...','Rendering 4 designs for you...','Almost ready...'];
    const longWaitMessages = ['Still working — great designs take a little longer...','Almost there, just polishing the details...','Quality takes a moment, thanks for your patience...'];
    const veryLongWaitMessages = ['This one is taking a bit longer than usual, but we are still on it...','Our servers are working hard on your custom design...','Thanks for sticking with us — your rug is being carefully crafted...','Almost certainly worth the wait, hang tight...'];
    const genStartTime = Date.now();
    let msgIdx = 0;
    let longMsgIdx = 0;
    let veryLongMsgIdx = 0;
    dom.loadingText.textContent = messages[0];
    const msgInterval = setInterval(() => {
      const elapsed = Date.now() - genStartTime;

      if (elapsed > 210000) {
        dom.loadingText.textContent = veryLongWaitMessages[veryLongMsgIdx % veryLongWaitMessages.length];
        veryLongMsgIdx++;
        dom.progressFill.style.width = '96%';
      } else if (elapsed > 90000) {
        dom.loadingText.textContent = longWaitMessages[longMsgIdx % longWaitMessages.length];
        longMsgIdx++;
        dom.progressFill.style.width = '92%';
      } else {
        msgIdx = (msgIdx + 1) % messages.length;
        dom.loadingText.textContent = messages[msgIdx];
        const pct = Math.min(90, 15 + msgIdx * 18);
        dom.progressFill.style.width = pct + '%';
      }
    }, 2500);

    const payload = {
      email:       CUSTOMER_EMAIL,
      style:       state.style,
      shape:       state.shape,
      size:        state.size.trim(),
      material:    state.material,
      colors:      state.colors,
      description: state.description || ''
    };

    try {
      // Step 1: kick off the job — returns immediately as "pending"
      const startRes = await fetch(API_BASE + '/api/ruggen/generate/', {
              method:'POST', headers:API_HEADERS, body:JSON.stringify(payload)
            });
      const startData = await startRes.json();

      // ✅ 3x generation limit — now ACTIVE (server-side 403 response)
      if (startRes.status===403 && startData.error==='generation_limit_reached') {
        clearInterval(msgInterval);
        state.gensUsed = MAX_GENS;
        dom.previewLoading.classList.remove('visible');
        dom.previewEmpty.style.display = 'block';
        showLimitScreen();
        state.isGenerating = false;
        dom.btnGenerate.classList.remove('loading');
        return;
      }
      if (!startRes.ok) {
    console.error('Full error response:', startData);
    throw new Error(startData.error || startData.detail || JSON.stringify(startData) || 'API error ' + startRes.status);
  }
      if (!startData.generation_id) throw new Error('No generation_id returned from API.');

      state.generationId = startData.generation_id;

      // Quota + price are already known from the initial response —
      // update them right away instead of waiting for images.
      state.gensUsed = startData.generations_used !== undefined ? startData.generations_used : state.gensUsed;
      state.gensRemaining = startData.generations_remaining !== undefined ? startData.generations_remaining : Math.max(0, MAX_GENS - state.gensUsed);
      updateGenCounter();
      if (startData.pricing) applyServerPricing(startData.pricing);

      const pollUrl = startData.poll_url || ('/api/ruggen/' + startData.generation_id + '/');

      // Step 2: poll until generated/failed
      dom.loadingText.textContent = messages[0];
      const finalData = await pollGeneration(pollUrl);

      clearInterval(msgInterval);
      dom.progressFill.style.width = '100%';

      // Pull images out of rug_images: [{index, base64_data}, ...]
      const rugImages = finalData.rug_images || finalData.images || [];
      const imageUrls = rugImages
        .slice()
        .sort((a, b) => (a.index ?? 0) - (b.index ?? 0))
        .map(img => {
          if (typeof img === 'string') return img;
          return img.base64_data || img.url || img.base64 || '';
        })
        .filter(Boolean);

      if (imageUrls.length===0) throw new Error('No images returned from API.');

      await sleep(250);
      showImagesGrid(imageUrls, state.generationId);

      // Prefer pricing from the final response if present, otherwise
      // keep whatever we already applied from the initial response.
      if (finalData.pricing) {
        applyServerPricing(finalData.pricing);
      } else if (!dom.priceBox.classList.contains('visible')) {
        displayPrice(state.size, state.material);
      }

      saveToStorage(); // persist so a refresh doesn't lose these 4 designs

      showToast('✨ ' + imageUrls.length + ' designs generated!', 'success');

      // ✅ 3x generation limit — disable button once limit reached
      if (state.gensUsed >= MAX_GENS) {
        dom.btnGenerate.disabled = true;
        if (dom.btnGenerateLabel) dom.btnGenerateLabel.textContent = 'Generation limit reached';
      }

    } catch(err) {
      clearInterval(msgInterval);
      console.error('Generation error:', err);
      dom.previewLoading.classList.remove('visible');
      dom.previewEmpty.style.display = 'block';
      showToast('Generation failed: ' + err.message, 'error');
    }

    state.isGenerating = false;
    dom.btnGenerate.classList.remove('loading');
    if (state.gensUsed < MAX_GENS) {
      dom.btnGenerate.disabled = false;
      if (dom.btnGenerateLabel) dom.btnGenerateLabel.textContent = '✨ Generate Designs';
    }
  }

  /* Image grid */
  function showImagesGrid(imageUrls, generationId) {
    state.generatedImages = imageUrls;
    state.generationId = generationId;
    dom.imagesGrid.innerHTML = imageUrls.map((url,i) => {
      const src = url.startsWith('data:')||url.startsWith('http') ? url : 'data:image/jpeg;base64,'+url;
     return `<div class="pmc-image-option" data-index="${i}" role="button" tabindex="0">
        <button class="pmc-image-option__zoom" data-index="${i}" type="button" aria-label="View full size">+</button>
        <img class="pmc-image-option__img" src="${src}" alt="Design ${i+1}" loading="lazy">
        <div class="pmc-image-option__overlay">
          <span class="pmc-image-option__num">Option ${i+1}</span>
          <span class="pmc-image-option__check">✓</span>
        </div>
      </div>`;
    }).join('');
    dom.imagesGrid.querySelectorAll('.pmc-image-option').forEach(el => {
      el.addEventListener('click', () => selectImage(parseInt(el.dataset.index)));
      el.addEventListener('keydown', e => { if (e.key==='Enter'||e.key===' ') selectImage(parseInt(el.dataset.index)); });
    });
    dom.imagesGrid.querySelectorAll('.pmc-image-option__zoom').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation(); // don't trigger card selection underneath
        openLightbox(parseInt(btn.dataset.index));
      });
    });
    dom.previewLoading.classList.remove('visible');
    dom.imagesGridWrap.classList.add('visible');
    dom.selectHint.className = 'pmc-images-select-hint';
    dom.selectHint.textContent = '👆 Click on a design to select it';
  }

  function selectImage(index) {
    state.selectedIndex = index;
    dom.imagesGrid.querySelectorAll('.pmc-image-option').forEach((el,i) => el.classList.toggle('selected', i===index));
    dom.selectHint.className = 'pmc-images-select-hint selected-hint';
    dom.selectHint.textContent = '✓ Option '+(index+1)+' selected — choose a quantity and click "Order Now"';
    dom.btnOrderWrap.classList.add('visible');
    saveToStorage();
  }
  /* Lightbox: full-size view of a generated design */
  /* History / Favorites modal */
  async function openListModal(kind) {
    dom.listModalTitle.textContent = kind === 'history' ? 'Recent Designs' : 'Saved Designs';
    dom.listModalItems.innerHTML = '<p style="text-align:center;color:#888;">Loading...</p>';
    dom.listModal.classList.add('visible');

    const endpoint = kind === 'history' ? '/api/ruggen/history/' : '/api/ruggen/favorites/';
    try {
      const res = await fetch(API_BASE + endpoint + '?email=' + encodeURIComponent(CUSTOMER_EMAIL), { headers: { 'ngrok-skip-browser-warning': 'true' } });
      const data = await res.json();
      const list = data.results || [];

      if (!list.length) {
        dom.listModalItems.innerHTML = '<p style="text-align:center;color:#888;">Nothing here yet.</p>';
        return;
      }

      dom.listModalItems.innerHTML = list.map(item => {
        const isFailed = item.status === 'failed' || !item.rug_images || !item.rug_images.length;
        const raw = (!isFailed && item.rug_images[0]) ? item.rug_images[0].base64_data : '';
        const src = raw && (raw.startsWith('data:') || raw.startsWith('http')) ? raw : (raw ? 'data:' + (item.rug_images[0].mime_type || 'image/jpeg') + ';base64,' + raw : '');
        const dateStr = item.created_at ? new Date(item.created_at).toLocaleDateString() : '';

        return `<div class="pmc-list-item ${isFailed ? 'pmc-list-item--failed' : ''}" data-id="${item.id}" ${isFailed ? 'data-failed="1"' : ''}>
          ${src ? `<img src="${src}" class="pmc-list-item__thumb">` : `<div class="pmc-list-item__thumb pmc-list-item__thumb--empty">⚠️</div>`}
          <div class="pmc-list-item__meta">
            <div>${item.style || ''} · ${item.material || ''}</div>
            <div style="color:#888;font-size:11px;">${dateStr}${isFailed ? ' · Failed' : ''}</div>
          </div>
        </div>`;
      }).join('');

      dom.listModalItems.querySelectorAll('.pmc-list-item').forEach(el => {
        if (el.dataset.failed) return;
        el.addEventListener('click', () => loadGeneration(el.dataset.id, kind));
      });
    } catch (err) {
      dom.listModalItems.innerHTML = '<p style="text-align:center;color:#f87171;">Could not load. Try again.</p>';
    }
  }

  function closeListModal() { dom.listModal.classList.remove('visible'); }

  async function loadGeneration(generationId, kind) {
    try {
      const res = await fetch(API_BASE + '/api/ruggen/' + generationId + '/', { headers: { 'ngrok-skip-browser-warning': 'true' } });
      const data = await res.json();
      const rugImages = data.rug_images || [];
      const imageUrls = rugImages.slice()
        .sort((a,b) => (a.index ?? 0) - (b.index ?? 0))
        .map(img => img.base64_data || '')
        .filter(Boolean);
      if (!imageUrls.length) throw new Error('No images found for this design.');

      dom.previewEmpty.style.display = 'none';
      showImagesGrid(imageUrls, data.id);
      if (data.pricing) applyServerPricing(data.pricing);

      state.isFavorited = !!data.is_favorite;
      dom.btnFavorite.textContent = state.isFavorited ? '❤️ Saved' : '🤍 Save This Design';
      dom.btnFavorite.classList.toggle('saved', state.isFavorited);

      saveToStorage();
      closeListModal();
      showToast('Loaded design.', 'success');
    } catch (err) {
      showToast('Could not load design: ' + err.message, 'error');
    }
  }

  /* Lightbox: full-size view of a generated design */
  let lightboxIndex = 0;

  function openLightbox(index) {
    if (!state.generatedImages.length) return;
    lightboxIndex = index;
    renderLightbox();
    dom.lightbox.classList.add('visible');
    document.addEventListener('keydown', handleLightboxKeydown);
  }

  function closeLightbox() {
    dom.lightbox.classList.remove('visible');
    document.removeEventListener('keydown', handleLightboxKeydown);
  }

  function renderLightbox() {
    const url = state.generatedImages[lightboxIndex];
    const src = url.startsWith('data:') || url.startsWith('http') ? url : 'data:image/jpeg;base64,' + url;
    dom.lightboxImg.src = src;
    dom.lightboxCaption.textContent = `Option ${lightboxIndex + 1} of ${state.generatedImages.length}`;
    dom.lightboxSelectBtn.textContent = (state.selectedIndex === lightboxIndex)
      ? '✓ Selected' : '✓ Select This Design';
  }

  function lightboxStep(delta) {
    const len = state.generatedImages.length;
    lightboxIndex = (lightboxIndex + delta + len) % len;
    renderLightbox();
  }

  function handleLightboxKeydown(e) {
    if (e.key === 'Escape') closeLightbox();
    else if (e.key === 'ArrowLeft') lightboxStep(-1);
    else if (e.key === 'ArrowRight') lightboxStep(1);
  }

  dom.lightboxClose.addEventListener('click', closeLightbox);
  dom.lightboxPrev.addEventListener('click', () => lightboxStep(-1));
  dom.lightboxNext.addEventListener('click', () => lightboxStep(1));
  dom.lightbox.addEventListener('click', (e) => { if (e.target === dom.lightbox) closeLightbox(); });
  dom.lightboxSelectBtn.addEventListener('click', () => {
    selectImage(lightboxIndex);
    dom.lightboxSelectBtn.textContent = '✓ Selected';
  });

  /* ✅ Save / Favorite a generated design */
  async function handleFavorite() {
    if (state.selectedIndex === null) { showToast('Please select a design first.', 'error'); return; }
    if (!state.generationId) return;

    const nextState = !state.isFavorited;
    dom.btnFavorite.disabled = true;

    try {
      const res = await fetch(API_BASE + '/api/ruggen/' + state.generationId + '/favorite/', {
        method:'POST', headers:API_HEADERS, body: JSON.stringify({ is_favorite: nextState })
      });
      if (!res.ok) throw new Error('Request failed ' + res.status);

      state.isFavorited = nextState;
      dom.btnFavorite.textContent = state.isFavorited ? '❤️ Saved' : '🤍 Save This Design';
      dom.btnFavorite.classList.toggle('saved', state.isFavorited);
      showToast(state.isFavorited ? 'Design saved!' : 'Removed from saved designs.', 'success');
      saveToStorage();
    } catch(err) {
      showToast('Could not save design: ' + err.message, 'error');
    }
    dom.btnFavorite.disabled = false;
  }

  /* ✅ Order Now — calls checkout API then redirects */
  async function handleOrder() {
    if (state.selectedIndex === null) { showToast('Please select a design first.', 'error'); return; }
    if (!state.generationId) { showToast('Please generate designs first.', 'error'); return; }

    dom.btnOrder.disabled = true;
    dom.checkoutLoading.classList.add('visible');

    try {
      const res = await fetch(API_BASE + '/api/ruggen/checkout/', {
        method: 'POST',
        headers: API_HEADERS,
        body: JSON.stringify({
          generation_id:      state.generationId,
          selected_rug_index: state.selectedIndex,
          quantity:           state.quantity || 1
        })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Checkout error ' + res.status);

      // ✅ Redirect to checkout URL from backend
      const checkoutUrl = data.checkout_url || data.invoice_url;
      if (checkoutUrl) {
        clearStorage(); // order placed — nothing left to restore
        window.location.href = checkoutUrl;
        return;
      }

      throw new Error('No checkout URL returned from API.');

    } catch(err) {
      console.error('Checkout error:', err);
      dom.checkoutLoading.classList.remove('visible');
      dom.btnOrder.disabled = false;
      showToast('Checkout failed: ' + err.message, 'error');
    }
  }

  /* Utils */
  function sleep(ms) { return new Promise(r => setTimeout(r,ms)); }
  function showToast(msg, type) {
    dom.toast.textContent = msg;
    dom.toast.className = 'pmc-toast '+(type||'');
    requestAnimationFrame(() => dom.toast.classList.add('visible'));
    setTimeout(() => dom.toast.classList.remove('visible'), 4000);
  }

  if (document.readyState==='loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
</script>

{% schema %}
{
  "name": "Rug Configurator",
  "tag": "section",
  "class": "pmc-section-wrapper",
  "settings": [
    { "type": "text", "id": "heading",    "label": "Heading",    "default": "Rug Configurator" },
    { "type": "text", "id": "subheading", "label": "Subheading", "default": "Design Your Perfect Custom Rug" }
  ],
  "presets": [{ "name": "Rug Configurator" }]
}
{% endschema %}