/**
 * Fichier  : /menus/main/assets/js/sticky.js
 * Fonction : comportement du menu « sticky » + compact mobile au scroll
 */

document.addEventListener("DOMContentLoaded", () => {

    const menu = document.querySelector(".menu");

    if (!menu) {
        return;
    }

    const menuBackground = menu.querySelector(".background");

    let lastScrollY = window.scrollY;
    let ticking = false;

    function updateMenuOnScroll() {

        const currentScrollY = window.scrollY;
        const isTop = currentScrollY === 0;
        const isScrollingDown = currentScrollY > lastScrollY;
        const isMobile = window.matchMedia("(max-width: 1024px)").matches;

        if (isTop) {

            menu.classList.add("nosticky");
            menu.classList.remove("sticky");

            if (menuBackground) {
                menuBackground.classList.add("hidden");
                menuBackground.classList.remove("fadeInDown");
            }

        } else {

            menu.classList.add("sticky");
            menu.classList.remove("nosticky");

            if (menuBackground) {
                menuBackground.classList.remove("hidden");
                menuBackground.classList.add("fadeInDown");
            }

        }

        if (isMobile && !isTop && isScrollingDown) {
            menu.classList.add("is-compact");
        } else {
            menu.classList.remove("is-compact");
        }

        lastScrollY = Math.max(currentScrollY, 0);
        ticking = false;

    }

    function requestTick() {

        if (!ticking) {
            window.requestAnimationFrame(updateMenuOnScroll);
            ticking = true;
        }

    }

    updateMenuOnScroll();

    window.addEventListener("scroll", requestTick, {
        passive: true
    });

});