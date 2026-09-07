/**
 * Fichier  : /features/back-to-top/assets/js/script.js
 * Fonction : bouton pour remonter tout en haut de la page
 */

const backToTop = document.querySelector('.back_to_top');

function toggleBackToTop() {
    if (!backToTop) return;

    if (window.scrollY !== 0) {
        backToTop.classList.add('BackToTop', 'backtopIn');
        backToTop.classList.remove('backtotopOut');
    } else {
        backToTop.classList.remove('backtopIn');
        backToTop.classList.add('backtotopOut');

        backToTop.addEventListener('animationend', () => {
            if (window.scrollY === 0) {
                backToTop.classList.remove('BackToTop', 'backtotopOut');
            }
        }, { once: true });
    }
}

window.addEventListener('scroll', toggleBackToTop);
toggleBackToTop();