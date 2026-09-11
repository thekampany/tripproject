    document.addEventListener("DOMContentLoaded", function () {
        const spinner = document.getElementById("loading-spinner");
        spinner.classList.remove("active");

        document.querySelectorAll("form").forEach(form => {
            form.addEventListener("submit", function () {
                spinner.classList.add("active");
            });
        });
    });

    window.addEventListener("pageshow", function () {
        const spinner = document.getElementById("loading-spinner");
        spinner.classList.remove("active");
    });
