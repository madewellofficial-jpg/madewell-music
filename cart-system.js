/**
 * MADEWELL MUSIC — Cart System v2.1
 * 모든 페이지 공용 장바구니 시스템
 *
 * v2.1 변경사항:
 * - PayPal 버튼만 표시 (카드 버튼 제거 — PayPal 결제창 안에서 카드 직접 입력 가능)
 * - 드로어 내부 스크롤 구조 개선 (PC/모바일 모두 결제 버튼까지 스크롤 가능)
 * - disable-funding=card,credit,venmo 파라미터 추가
 */
(function () {
  'use strict';

  /* ══════════════════════════════════════════
     PRODUCTS — 상품 추가 시 여기에만 추가
  ══════════════════════════════════════════ */
  var PRODUCTS = {
    'su-cd':     { name:'Still UNFINISHED', sub:'2ND SOLO ALBUM',         usd:25, krw:35000, img:'images/STILL UNFINIHSED 앨범자료/2nd ALBUM MAIN.jpg' },
    'mama-btee': { name:'MAMA Black Tee',   sub:'MAMA : THE ETERNAL LOVE', usd:18, krw:29000, img:'images/MAMA_TEE_BLK.jpg.png' },
    'mama-wtee': { name:'MAMA White Tee',   sub:'MAMA : THE ETERNAL LOVE', usd:13, krw:18000, img:'images/MAMA_TEE_WHT1.jpg.png' },
    'su-btee':   { name:'SU Black Tee',     sub:'STILL UNFINISHED',        usd:22, krw:32000, img:'images/2nd_BLACK1.jpg' },
    'su-wtee':   { name:'SU White Tee',     sub:'STILL UNFINISHED',        usd:22, krw:32000, img:'images/2nd_WHITE1.jpg' },
    'su-hood':   { name:'SU Black Hoodie',  sub:'STILL UNFINISHED',        usd:47, krw:68000, img:'images/2nd_BLACKHOOD1.jpg' },
  };

  /* ══════════════════════════════════════════
     STATE
  ══════════════════════════════════════════ */
  var cart = [];
  var paypalRendered = false;
  var paypalLoading  = false;

  try { cart = JSON.parse(localStorage.getItem('mw_cart') || '[]'); } catch (e) { cart = []; }
  function saveCart() { try { localStorage.setItem('mw_cart', JSON.stringify(cart)); } catch (e) {} }

  /* ══════════════════════════════════════════
     CSS
  ══════════════════════════════════════════ */
  function injectCSS() {
    var s = document.createElement('style');
    s.id = 'mw-cart-css';
    s.textContent = [
      /* 플로팅 카트 버튼 */
      '.mw-fab{position:fixed;bottom:32px;right:32px;z-index:350;width:54px;height:54px;border-radius:50%;',
      'background:rgba(65,168,182,.92);border:none;cursor:pointer;display:flex;align-items:center;',
      'justify-content:center;box-shadow:0 4px 24px rgba(0,0,0,.45);transition:background .2s,transform .2s;color:#040e12;}',
      '.mw-fab:hover{background:rgba(80,185,200,1);transform:scale(1.07);}',
      '.mw-fab svg{width:22px;height:22px;}',
      '.mw-fab-badge{position:absolute;top:-3px;right:-3px;min-width:18px;height:18px;padding:0 4px;border-radius:9px;',
      'background:#fff;color:#040e12;font-size:8px;font-weight:700;display:none;align-items:center;',
      'justify-content:center;font-family:Montserrat,sans-serif;border:2px solid rgba(65,168,182,.85);}',

      /* Overlay */
      '.mw-overlay{position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:500;opacity:0;',
      'pointer-events:none;transition:opacity .3s;backdrop-filter:blur(3px);-webkit-backdrop-filter:blur(3px);}',
      '.mw-overlay.open{opacity:1;pointer-events:all;}',

      /* Drawer — 전체 높이 고정, 내부만 스크롤 */
      '.mw-drawer{position:fixed;top:0;right:0;bottom:0;width:420px;max-width:100vw;',
      'background:#060f14;border-left:1px solid rgba(255,255,255,.08);z-index:600;',
      'transform:translateX(100%);transition:transform .42s cubic-bezier(.22,1,.36,1);',
      'display:flex;flex-direction:column;font-family:Montserrat,sans-serif;overflow:hidden;}',
      '.mw-drawer.open{transform:translateX(0);}',
      '@media(max-width:480px){.mw-drawer{width:100vw;}}',

      /* Head — 고정 */
      '.mw-head{display:flex;align-items:center;justify-content:space-between;',
      'padding:20px 24px;border-bottom:1px solid rgba(255,255,255,.07);flex-shrink:0;}',
      '.mw-head-left{display:flex;align-items:center;gap:12px;}',
      '.mw-head-title{font-size:10px;font-weight:700;letter-spacing:.36em;text-transform:uppercase;color:rgba(255,255,255,.65);}',
      '.mw-head-count{font-size:9px;font-weight:600;color:rgba(95,200,215,.6);letter-spacing:.14em;}',
      '.mw-x{background:none;border:none;color:rgba(255,255,255,.28);cursor:pointer;',
      'padding:6px;font-size:18px;line-height:1;transition:color .2s;}',
      '.mw-x:hover{color:rgba(255,255,255,.8);}',

      /* Body — 이 영역이 스크롤됨 (items + footer 포함) */
      '.mw-body{flex:1;overflow-y:auto;overflow-x:hidden;',
      'scrollbar-width:thin;scrollbar-color:rgba(255,255,255,.08) transparent;',
      'display:flex;flex-direction:column;}',
      '.mw-body::-webkit-scrollbar{width:3px;}',
      '.mw-body::-webkit-scrollbar-thumb{background:rgba(255,255,255,.1);}',

      /* Empty state */
      '.mw-empty{flex:1;display:flex;align-items:center;justify-content:center;',
      'flex-direction:column;gap:10px;min-height:200px;}',
      '.mw-empty-lbl{font-size:9px;font-weight:700;letter-spacing:.3em;text-transform:uppercase;color:rgba(255,255,255,.12);}',
      '.mw-empty-sub{font-size:11px;color:rgba(255,255,255,.09);font-weight:300;}',

      /* Cart item row */
      '.mw-item{display:flex;gap:14px;padding:18px 24px;border-bottom:1px solid rgba(255,255,255,.05);align-items:flex-start;}',
      '.mw-thumb{width:68px;height:86px;flex-shrink:0;overflow:hidden;background:#0a1c22;}',
      '.mw-thumb img{width:100%;height:100%;object-fit:cover;object-position:50% 15%;}',
      '.mw-info{flex:1;min-width:0;}',
      '.mw-iname{font-family:"Cormorant Garamond",serif;font-size:16px;font-weight:300;color:#fff;line-height:1.2;margin-bottom:3px;}',
      '.mw-imeta{font-size:7.5px;font-weight:700;letter-spacing:.22em;text-transform:uppercase;color:rgba(95,200,215,.45);margin-bottom:8px;}',
      '.mw-iprice{font-size:11px;font-weight:600;color:rgba(255,255,255,.55);}',
      '.mw-ctrl{display:flex;flex-direction:column;align-items:center;gap:6px;flex-shrink:0;padding-top:2px;}',
      '.mw-qbtn{width:26px;height:26px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);',
      'color:rgba(255,255,255,.65);cursor:pointer;font-size:14px;display:flex;align-items:center;',
      'justify-content:center;transition:background .15s;font-family:Montserrat,sans-serif;}',
      '.mw-qbtn:hover{background:rgba(255,255,255,.12);}',
      '.mw-qnum{font-size:12px;font-weight:700;color:rgba(255,255,255,.85);min-width:20px;text-align:center;}',
      '.mw-del{background:none;border:none;cursor:pointer;color:rgba(255,255,255,.15);',
      'padding:3px;margin-top:4px;transition:color .2s;display:flex;}',
      '.mw-del:hover{color:rgba(255,80,80,.65);}',
      '.mw-del svg{width:11px;height:11px;}',

      /* Footer — items 아래 붙어있고 같이 스크롤됨 */
      '.mw-ft{padding:20px 24px 36px;border-top:1px solid rgba(255,255,255,.07);background:rgba(5,12,16,.9);}',
      '.mw-ship{font-size:8px;color:rgba(255,255,255,.18);letter-spacing:.12em;line-height:1.9;',
      'margin-bottom:16px;font-weight:500;text-transform:uppercase;}',
      '.mw-trow{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:18px;}',
      '.mw-tlabel{font-size:9px;font-weight:700;letter-spacing:.34em;text-transform:uppercase;color:rgba(255,255,255,.3);}',
      '#mw-total{font-family:"Cormorant Garamond",serif;font-size:26px;font-weight:300;color:#fff;}',

      /* PayPal 버튼 영역 */
      '#mw-pp{min-height:48px;margin-bottom:12px;}',
      '.mw-card-note{font-size:9px;color:rgba(255,255,255,.22);letter-spacing:.08em;',
      'text-align:center;line-height:1.8;padding:0 4px;}',
      '.mw-card-note strong{color:rgba(95,200,215,.5);font-weight:600;}',
      '.mw-ppload{font-size:9px;color:rgba(255,255,255,.2);letter-spacing:.2em;',
      'text-transform:uppercase;text-align:center;padding:16px 0;}',

      /* Add to Cart 버튼 (상품 페이지용) */
      '.mw-add-btn{display:flex;align-items:center;justify-content:center;gap:10px;',
      'padding:16px 28px;background:rgba(65,168,182,.9);color:#040e12;',
      'font-size:10px;font-weight:700;letter-spacing:.22em;text-transform:uppercase;',
      'border:none;width:100%;cursor:pointer;font-family:Montserrat,sans-serif;transition:background .2s;}',
      '.mw-add-btn:hover{background:rgba(80,185,200,1);}',
      '.mw-add-btn svg{width:16px;height:16px;}',

      /* Toast */
      '@keyframes mwfs{from{opacity:0;transform:translateX(-50%) translateY(-8px)}',
      'to{opacity:1;transform:translateX(-50%) translateY(0)}}',
      '.mw-toast{position:fixed;top:28px;left:50%;transform:translateX(-50%);',
      'background:rgba(65,168,182,.96);color:#040e12;font-family:Montserrat,sans-serif;',
      'font-size:10px;font-weight:700;letter-spacing:.18em;padding:14px 28px;z-index:9999;',
      'text-transform:uppercase;animation:mwfs .3s ease;white-space:nowrap;}',
    ].join('');
    document.head.appendChild(s);
  }

  /* ══════════════════════════════════════════
     HTML INJECTION
  ══════════════════════════════════════════ */
  function injectHTML() {
    /* 플로팅 버튼 */
    var fab = document.createElement('button');
    fab.className = 'mw-fab';
    fab.setAttribute('aria-label', '장바구니 열기');
    fab.onclick = open;
    fab.innerHTML = [
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">',
        '<path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z"/>',
        '<line x1="3" y1="6" x2="21" y2="6"/>',
        '<path d="M16 10a4 4 0 01-8 0"/>',
      '</svg>',
      '<span class="mw-fab-badge" id="mw-badge"></span>',
    ].join('');
    document.body.appendChild(fab);

    /* Overlay */
    var ov = document.createElement('div');
    ov.id = 'mw-overlay';
    ov.className = 'mw-overlay';
    ov.onclick = close;
    document.body.appendChild(ov);

    /* Drawer
       구조: head(고정) + body(스크롤) = [items + empty + footer]
       → body가 스크롤되므로 카드 폼이 펼쳐져도 결제 버튼까지 스크롤 가능
    */
    var dr = document.createElement('div');
    dr.id = 'mw-drawer';
    dr.className = 'mw-drawer';
    dr.innerHTML = [
      '<div class="mw-head">',
      '  <div class="mw-head-left">',
      '    <div class="mw-head-title">CART</div>',
      '    <div class="mw-head-count" id="mw-cnt"></div>',
      '  </div>',
      '  <button class="mw-x" onclick="mwCart.close()">✕</button>',
      '</div>',

      /* mw-body: 이 전체가 스크롤됨 */
      '<div class="mw-body" id="mw-body">',
      '  <div id="mw-items"></div>',
      '  <div class="mw-empty" id="mw-empty">',
      '    <div class="mw-empty-lbl">EMPTY CART</div>',
      '    <div class="mw-empty-sub">아직 담긴 상품이 없어요</div>',
      '  </div>',
      '  <div class="mw-ft" id="mw-ft" style="display:none">',
      '    <div class="mw-ship">합배송 가능 — 주문 확인 후 배송비를 별도 안내드립니다</div>',
      '    <div class="mw-trow">',
      '      <span class="mw-tlabel">TOTAL</span>',
      '      <span id="mw-total">$0.00</span>',
      '    </div>',
      '    <div id="mw-pp"></div>',
      '    <div class="mw-card-note">',
      '      PayPal 결제창 안에서 <strong>신용 · 직불카드 직접 입력</strong> 가능<br>',
      '      계정 없이 카드로만 결제하려면 결제창에서 "Pay with Debit or Credit Card" 클릭',
      '    </div>',
      '  </div>',
      '</div>',
    ].join('');
    document.body.appendChild(dr);
  }

  /* ══════════════════════════════════════════
     BADGE
  ══════════════════════════════════════════ */
  function updateBadge() {
    var n = cart.reduce(function (s, i) { return s + i.qty; }, 0);
    var b = document.getElementById('mw-badge');
    if (!b) return;
    b.textContent = n || '';
    b.style.display = n > 0 ? 'flex' : 'none';
  }

  /* ══════════════════════════════════════════
     OPEN / CLOSE
  ══════════════════════════════════════════ */
  function open() {
    document.getElementById('mw-drawer').classList.add('open');
    document.getElementById('mw-overlay').classList.add('open');
    document.body.style.overflow = 'hidden';
    render();
    loadPayPal();
  }

  function close() {
    document.getElementById('mw-drawer').classList.remove('open');
    document.getElementById('mw-overlay').classList.remove('open');
    document.body.style.overflow = '';
  }

  /* ══════════════════════════════════════════
     ADD TO CART
     productId: PRODUCTS 키
     size: 'M' 등 문자열, 또는 null (앨범 등)
  ══════════════════════════════════════════ */
  function addToCart(productId, size) {
    var p = PRODUCTS[productId];
    if (!p) { console.warn('mwCart: unknown product', productId); return; }
    var cartId = size ? productId + '-' + size : productId;
    var existing = null;
    for (var i = 0; i < cart.length; i++) {
      if (cart[i].cartId === cartId) { existing = cart[i]; break; }
    }
    if (existing) {
      existing.qty++;
    } else {
      cart.push({
        cartId: cartId, productId: productId,
        name: p.name, sub: p.sub,
        size: size || null,
        usd: p.usd, krw: p.krw, img: p.img,
        qty: 1,
      });
    }
    saveCart();
    updateBadge();
    open();
  }

  /* ══════════════════════════════════════════
     RENDER
  ══════════════════════════════════════════ */
  function render() {
    var itemsEl = document.getElementById('mw-items');
    var emptyEl = document.getElementById('mw-empty');
    var ftEl    = document.getElementById('mw-ft');
    var cntEl   = document.getElementById('mw-cnt');
    if (!itemsEl) return;

    var totalQty = cart.reduce(function (s, i) { return s + i.qty; }, 0);
    if (cntEl) cntEl.textContent = totalQty > 0 ? totalQty + ' item' + (totalQty > 1 ? 's' : '') : '';

    if (cart.length === 0) {
      itemsEl.innerHTML = '';
      if (emptyEl) emptyEl.style.display = 'flex';
      if (ftEl)    ftEl.style.display    = 'none';
      var pp = document.getElementById('mw-pp');
      if (pp) pp.innerHTML = '';
      paypalRendered = false;
      return;
    }

    if (emptyEl) emptyEl.style.display = 'none';
    if (ftEl)    ftEl.style.display    = 'block';

    itemsEl.innerHTML = cart.map(function (item, idx) {
      return (
        '<div class="mw-item">' +
          '<div class="mw-thumb"><img src="' + item.img + '" alt="' + item.name + '" onerror="this.style.display=\'none\'"></div>' +
          '<div class="mw-info">' +
            '<div class="mw-iname">' + item.name + '</div>' +
            '<div class="mw-imeta">' + item.sub + (item.size ? ' · ' + item.size : '') + '</div>' +
            '<div class="mw-iprice">$' + (item.usd * item.qty).toFixed(2) + '</div>' +
          '</div>' +
          '<div class="mw-ctrl">' +
            '<button class="mw-qbtn" onclick="mwCart.changeQty(' + idx + ',1)">+</button>' +
            '<span class="mw-qnum">' + item.qty + '</span>' +
            '<button class="mw-qbtn" onclick="mwCart.changeQty(' + idx + ',-1)">−</button>' +
            '<button class="mw-del" onclick="mwCart.removeItem(' + idx + ')">' +
              '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 3l10 10M13 3L3 13"/></svg>' +
            '</button>' +
          '</div>' +
        '</div>'
      );
    }).join('');

    /* 총액 업데이트 */
    var total = cart.reduce(function (s, i) { return s + i.usd * i.qty; }, 0);
    var totalEl = document.getElementById('mw-total');
    if (totalEl) totalEl.textContent = '$' + total.toFixed(2);

    if (!paypalRendered) renderPayPal();

    /* 결제 버튼이 보이도록 body 스크롤 최하단으로 */
    var body = document.getElementById('mw-body');
    if (body) {
      setTimeout(function () {
        var pp = document.getElementById('mw-pp');
        if (pp) pp.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }, 300);
    }
  }

  function changeQty(idx, delta) {
    if (!cart[idx]) return;
    cart[idx].qty = Math.max(1, cart[idx].qty + delta);
    saveCart();
    updateBadge();
    paypalRendered = false;
    render();
  }

  function removeItem(idx) {
    cart.splice(idx, 1);
    saveCart();
    updateBadge();
    paypalRendered = false;
    render();
  }

  /* ══════════════════════════════════════════
     PAYPAL
     disable-funding=card,credit,venmo → PayPal 버튼만 표시
     PayPal 결제창 안에서 "Pay with Debit or Credit Card" 클릭하면 카드 결제 가능
  ══════════════════════════════════════════ */
  var PAYPAL_CLIENT_ID = 'AZnXhAax6PaJvdcSZvthoGrE6JQr2FPha2jzA5AMX95s5e4qvlXeY3QjOjUIiwZzeGTLxKE1F-XLxPMg';

  function loadPayPal() {
    if (typeof paypal !== 'undefined' || paypalLoading) return;
    paypalLoading = true;
    var sc = document.createElement('script');
    sc.src = 'https://www.paypal.com/sdk/js?client-id=' + PAYPAL_CLIENT_ID +
             '&currency=USD';
    sc.onload = function () {
      paypalLoading = false;
      if (!paypalRendered && cart.length > 0) renderPayPal();
    };
    document.head.appendChild(sc);
  }

  function renderPayPal() {
    var container = document.getElementById('mw-pp');
    if (!container || cart.length === 0) return;
    if (typeof paypal === 'undefined') {
      container.innerHTML = '<div class="mw-ppload">PayPal 로딩 중...</div>';
      return;
    }
    container.innerHTML = '';

    paypal.Buttons({
      style: { layout: 'vertical', color: 'gold', shape: 'rect', label: 'pay', height: 50 },

      /* 결제 버튼 클릭 시 — 장바구니 현재 내용으로 주문서 실시간 생성 */
      createOrder: function (data, actions) {
        var total = cart.reduce(function (s, i) { return s + i.usd * i.qty; }, 0);
        return actions.order.create({
          purchase_units: [{
            description: 'MADEWELL MUSIC Official Store',
            amount: {
              currency_code: 'USD',
              value: total.toFixed(2),
              breakdown: { item_total: { currency_code: 'USD', value: total.toFixed(2) } },
            },
            items: cart.map(function (item) {
              return {
                name: item.name + (item.size ? ' (' + item.size + ')' : ''),
                description: item.sub,
                unit_amount: { currency_code: 'USD', value: item.usd.toFixed(2) },
                quantity: String(item.qty),
              };
            }),
          }],
        });
      },

      onApprove: function (data, actions) {
        return actions.order.capture().then(function (details) {
          var name = details.payer && details.payer.name ? details.payer.name.given_name : '';
          cart = [];
          saveCart();
          updateBadge();
          paypalRendered = false;
          close();
          toast('✓ 결제 완료' + (name ? ' · 감사합니다, ' + name + '님' : ''));
        });
      },

      onError: function (err) {
        console.error('PayPal error:', err);
        alert('결제 중 오류가 발생했습니다. 다시 시도해주세요.');
      },

      onCancel: function () { /* 취소 시 드로어 유지 */ },
    }).render('#mw-pp');

    paypalRendered = true;
  }

  /* ══════════════════════════════════════════
     TOAST
  ══════════════════════════════════════════ */
  function toast(msg) {
    var el = document.createElement('div');
    el.className = 'mw-toast';
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, 5000);
  }

  /* ══════════════════════════════════════════
     INIT
  ══════════════════════════════════════════ */
  function init() {
    if (document.getElementById('mw-cart-css')) return; /* 중복 실행 방지 */
    injectCSS();
    injectHTML();
    updateBadge();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  /* ══════════════════════════════════════════
     PUBLIC API
  ══════════════════════════════════════════ */
  window.mwCart = {
    open:       open,
    close:      close,
    addToCart:  addToCart,
    changeQty:  changeQty,
    removeItem: removeItem,
  };

})();
