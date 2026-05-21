(function () {
    const form = document.getElementById("venue-dashboard-filters");
    if (!form) {
        return;
    }

    const viewSelect = document.getElementById("dashboard-view");
    const dateInput = document.getElementById("dashboard-date");
    const searchInput = document.getElementById("dashboard-search");
    const dateWrapper = document.getElementById("dashboard-date-wrapper");
    const statusWrapper = document.getElementById("dashboard-status-wrapper");
    const periodViews = new Set(["day", "week", "month"]);
    const historyViews = new Set(["past", "all"]);

    function todayIso() {
        const d = new Date();
        const m = String(d.getMonth() + 1).padStart(2, "0");
        const day = String(d.getDate()).padStart(2, "0");
        return `${d.getFullYear()}-${m}-${day}`;
    }

    function toggleFilterFields() {
        if (!viewSelect) {
            return;
        }
        const period = periodViews.has(viewSelect.value);
        const history = historyViews.has(viewSelect.value);
        if (dateWrapper) {
            dateWrapper.classList.toggle("d-none", !period);
        }
        if (statusWrapper) {
            statusWrapper.classList.toggle("d-none", history);
        }
        if (viewSelect.value === "day" && dateInput && !dateInput.dataset.userSet) {
            dateInput.value = todayIso();
        }
    }

    function submitFilters() {
        toggleFilterFields();
        if (typeof form.requestSubmit === "function") {
            form.requestSubmit();
        } else {
            form.submit();
        }
    }

    if (dateInput) {
        dateInput.addEventListener("change", function () {
            dateInput.dataset.userSet = "1";
        });
    }

    form.querySelectorAll("select, input[type='date']").forEach(function (el) {
        el.addEventListener("change", submitFilters);
    });

    if (searchInput) {
        searchInput.addEventListener("keydown", function (e) {
            if (e.key === "Enter") {
                e.preventDefault();
                submitFilters();
            }
        });
        if (searchInput.value) {
            searchInput.focus();
            const end = searchInput.value.length;
            searchInput.setSelectionRange(end, end);
        }
    }

    toggleFilterFields();
})();
