// static/js/currency-format.js - 전역 천 단위 콤마 포맷팅

(function() {
    'use strict';
    
    // 숫자 포맷팅 함수
    function formatNumber(num) {
        return parseInt(num).toLocaleString();
    }
    
    // 숫자만 추출
    function extractNumber(str) {
        return str.replace(/[^\d]/g, '');
    }
    
    // 입력 필드 포맷팅
    function formatInputField(input) {
        const value = extractNumber(input.value);
        if (value) {
            input.value = formatNumber(value);
        }
    }
    
    // 자동 감지할 선택자들
    const INPUT_SELECTORS = [
        'input[type="number"]',
        'input[data-currency]',
        'input[name$="_day"]',
        'input[name$="_night"]', 
        'input[name$="_midnight"]',
        'input[name*="cost"]',
        'input[name*="price"]',
        'input[name*="amount"]',
        'input[name*="contract"]',
        '.currency-input',
        '.cost-input',
        '.money-input'
    ];
    
    const DISPLAY_SELECTORS = [
        '.currency-display',
        '.number-cell',
        '.cost-display',
        '.amount-display'
    ];
    
    // 초기화 함수
    function initCurrencyFormatting() {
        // 입력 필드 처리
        document.querySelectorAll(INPUT_SELECTORS.join(',')).forEach(input => {
            // 초기값 포맷팅
            if (input.value && !isNaN(extractNumber(input.value))) {
                formatInputField(input);
            }
            
            // 실시간 포맷팅
            input.addEventListener('input', function() {
                formatInputField(this);
            });
            
            // 포커스 아웃 시 재포맷팅
            input.addEventListener('blur', function() {
                formatInputField(this);
            });
            
            // 폼 제출 전 콤마 제거
            const form = input.closest('form');
            if (form && !form.hasAttribute('data-currency-processed')) {
                form.setAttribute('data-currency-processed', 'true');
                form.addEventListener('submit', function() {
                    document.querySelectorAll(INPUT_SELECTORS.join(',')).forEach(inp => {
                        if (inp.value) {
                            inp.value = extractNumber(inp.value);
                        }
                    });
                });
            }
        });
        
        // 표시용 요소 처리
        document.querySelectorAll(DISPLAY_SELECTORS.join(',')).forEach(element => {
            const text = element.textContent.trim();
            const number = extractNumber(text);
            if (number && !isNaN(number) && number.length >= 4) {
                // 원래 텍스트에서 숫자 부분만 교체
                element.textContent = text.replace(/\d{4,}/, formatNumber(number));
            }
        });
    }
    
    // DOM 준비 시 초기화
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCurrencyFormatting);
    } else {
        initCurrencyFormatting();
    }
    
    // 동적 콘텐츠 감지 (AJAX 로딩 등)
    if (window.MutationObserver) {
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.addedNodes.length) {
                    setTimeout(initCurrencyFormatting, 100);
                }
            });
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }
    
    // 전역 함수로 노출
    window.formatCurrency = formatNumber;
    window.extractCurrencyNumber = extractNumber;
})();