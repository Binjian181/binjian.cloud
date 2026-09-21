/**
 * 公共 JS 文件 - 所有页面共用
 * 版本: 2.0
 */
(function() {
    'use strict';
    
    // ========== SVG 图标定义 ==========
    var ICONS = {
        sun: '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>',
        moon: '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>',
        menu: '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>',
        x: '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>'
    };
    
    // ========== DOM 元素缓存 ==========
    var root = document.documentElement;
    var themeToggle = document.getElementById('themeToggle');
    var themeToggleMobile = document.getElementById('themeToggleMobile');
    var menuToggle = document.getElementById('menuToggle');
    var navSidebar = document.getElementById('navSidebar');
    
    // ========== 主题管理 ==========
    var ThemeManager = {
        STORAGE_KEY: 'theme',
        
        init: function() {
            var savedTheme = this.getSavedTheme();
            if (savedTheme) {
                root.setAttribute('data-theme', savedTheme);
            }
            this.updateAllIcons(this.getCurrentTheme());
        },
        
        getSavedTheme: function() {
            try {
                return localStorage.getItem(this.STORAGE_KEY);
            } catch (e) {
                return null;
            }
        },
        
        getCurrentTheme: function() {
            var currentTheme = root.getAttribute('data-theme');
            if (!currentTheme) {
                var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                currentTheme = prefersDark ? 'dark' : 'light';
            }
            return currentTheme;
        },
        
        toggle: function() {
            var currentTheme = this.getCurrentTheme();
            var newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            
            root.setAttribute('data-theme', newTheme);
            
            try {
                localStorage.setItem(this.STORAGE_KEY, newTheme);
            } catch (e) {
                // localStorage 不可用时静默失败
            }
            
            this.updateAllIcons(newTheme);
            this.updateAriaPressed(newTheme);
        },
        
        updateAllIcons: function(theme) {
            var icon = theme === 'dark' ? ICONS.sun : ICONS.moon;
            var title = theme === 'dark' ? '切换到亮色模式' : '切换到暗色模式';
            
            var buttons = document.querySelectorAll('.theme-toggle, .theme-toggle-mobile');
            buttons.forEach(function(btn) {
                var textSpan = btn.querySelector('.theme-text');
                if (textSpan) {
                    btn.innerHTML = icon + '<span class="theme-text">' + textSpan.textContent + '</span>';
                } else {
                    btn.innerHTML = icon;
                }
                btn.title = title;
            });
        },
        
        updateAriaPressed: function(theme) {
            var buttons = document.querySelectorAll('.theme-toggle, .theme-toggle-mobile');
            buttons.forEach(function(btn) {
                btn.setAttribute('aria-pressed', theme === 'dark' ? 'true' : 'false');
            });
        }
    };
    
    // ========== 移动端菜单管理 ==========
    var MenuManager = {
        isOpen: false,
        
        toggle: function() {
            this.isOpen = !this.isOpen;
            
            if (navSidebar) {
                navSidebar.classList.toggle('open', this.isOpen);
            }
            
            if (menuToggle) {
                menuToggle.innerHTML = this.isOpen ? ICONS.x : ICONS.menu;
                menuToggle.setAttribute('aria-expanded', this.isOpen ? 'true' : 'false');
            }
        },
        
        close: function() {
            if (!this.isOpen) return;
            
            this.isOpen = false;
            
            if (navSidebar) {
                navSidebar.classList.remove('open');
            }
            
            if (menuToggle) {
                menuToggle.innerHTML = ICONS.menu;
                menuToggle.setAttribute('aria-expanded', 'false');
            }
        }
    };
    
    // ========== 事件绑定 ==========
    function bindEvents() {
        // 主题切换
        if (themeToggle) {
            themeToggle.addEventListener('click', function() {
                ThemeManager.toggle();
            });
        }
        
        if (themeToggleMobile) {
            themeToggleMobile.addEventListener('click', function() {
                ThemeManager.toggle();
            });
        }
        
        // 移动端菜单
        if (menuToggle) {
            menuToggle.addEventListener('click', function(e) {
                e.stopPropagation();
                MenuManager.toggle();
            });
        }
        
        // 点击导航链接后关闭菜单
        var navLinks = document.querySelectorAll('.nav-btn');
        navLinks.forEach(function(link) {
            link.addEventListener('click', function() {
                MenuManager.close();
            });
        });
        
        // 点击菜单外部关闭菜单
        document.addEventListener('click', function(e) {
            if (menuToggle && navSidebar) {
                var isToggle = menuToggle.contains(e.target);
                var isInSidebar = navSidebar.contains(e.target);
                
                if (!isToggle && !isInSidebar && MenuManager.isOpen) {
                    MenuManager.close();
                }
            }
        });
        
        // ESC 键关闭菜单
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                MenuManager.close();
            }
        });
        
        // 监听系统主题变化
        var mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        if (mediaQuery.addEventListener) {
            mediaQuery.addEventListener('change', function(e) {
                if (!ThemeManager.getSavedTheme()) {
                    ThemeManager.updateAllIcons(e.matches ? 'dark' : 'light');
                }
            });
        }
    }
    
    // ========== 初始化 ==========
    function init() {
        ThemeManager.init();
        bindEvents();
    }
    
    // DOM 加载完成后初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
