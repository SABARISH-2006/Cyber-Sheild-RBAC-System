document.addEventListener("DOMContentLoaded", function () {
    // 1. Auto fade-out for bootstrap alert messages
    const alerts = document.querySelectorAll(".alert-dismissible");
    alerts.forEach(function (alert) {
        setTimeout(function () {
            // Use bootstrap transition classes if available, or basic fade-out
            alert.style.transition = "opacity 0.6s ease";
            alert.style.opacity = "0";
            setTimeout(function () {
                alert.remove();
            }, 600);
        }, 5000);
    });

    // 2. Add confirmation warnings for destructive form submissions
    const deleteForms = document.querySelectorAll(".form-delete-confirm");
    deleteForms.forEach(form => {
        form.addEventListener("submit", function (e) {
            const confirmed = confirm("WARNING: Are you sure you want to proceed with this destructive security operation?");
            if (!confirmed) {
                e.preventDefault();
            }
        });
    });

    // 3. Simple sidebar toggle for responsive mobile views
    const sidebarToggle = document.getElementById("sidebarToggle");
    const sidebar = document.querySelector(".sidebar");
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener("click", function () {
            sidebar.classList.toggle("show");
        });
    }
});
