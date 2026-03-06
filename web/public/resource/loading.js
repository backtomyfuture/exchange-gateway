/**
 * 初始化加载效果的svg格式logo
 * @param {string} id - 元素id
 */
 function initSvgLogo(id) {
  const svgStr = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500" fill="none"><circle cx="250" cy="250" r="240" fill="#f8fafc"/><rect x="100" y="150" width="300" height="200" rx="20" fill="currentColor" opacity="0.85"/><path d="M100 170 L250 280 L400 170" fill="currentColor"/><path d="M100 170 L250 280 L400 170" stroke="currentColor" stroke-width="3" fill="none" opacity="0.6"/><path d="M100 350 L180 250" stroke="currentColor" stroke-width="2" fill="none" opacity="0.3"/><path d="M400 350 L320 250" stroke="currentColor" stroke-width="2" fill="none" opacity="0.3"/><g transform="translate(350, 100)"><path d="M10 30 L30 10 L30 20 L50 20 L50 40 L30 40 L30 50 Z" fill="#10b981"/><path d="M50 10 L30 30 L30 20 L10 20 L10 0 L30 0 L30 -10 Z" fill="#ef4444" transform="rotate(180 30 20)"/></g><circle cx="130" cy="320" r="8" fill="currentColor" opacity="0.4"/><circle cx="155" cy="320" r="8" fill="currentColor" opacity="0.4"/><circle cx="180" cy="320" r="8" fill="currentColor" opacity="0.4"/></svg>`
  const appEl = document.querySelector(id)
  const div = document.createElement('div')
  div.innerHTML = svgStr
  if (appEl) {
    appEl.appendChild(div)
  }
}

function addThemeColorCssVars() {
  const key = '__THEME_COLOR__'
  const defaultColor = '#F4511E'
  const themeColor = window.localStorage.getItem(key) || defaultColor
  const cssVars = `--primary-color: ${themeColor}`
  document.documentElement.style.cssText = cssVars
}

addThemeColorCssVars()

initSvgLogo('#loadingLogo')
