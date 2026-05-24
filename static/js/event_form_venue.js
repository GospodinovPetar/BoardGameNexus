(function () {
    const form = document.getElementById("event-form");
    if (!form) return;

    const venueSelect = document.getElementById("id_venue");
    const locationWrapper = document.getElementById("location-field-wrapper");
    const schedulePanel = document.getElementById("venue-schedule-panel");
    const independentFields = document.getElementById("independent-schedule-fields");
    const playersOutsideVenue = document.getElementById("players-outside-venue");
    const eventDateInput = document.getElementById("id_event_date");
    const startTimeInput = document.getElementById("id_start_time");
    const endTimeInput = document.getElementById("id_venue_end_time");
    const slotsHiddenInput = document.getElementById("id_venue_time_slots");
    const maxPlayersInput = document.getElementById("id_max_players");
    const dateTimeInput = document.getElementById("id_date_time");
    const endDateTimeInput = document.getElementById("id_event_end_datetime");
    const hourGridBody = document.getElementById("venue-hour-grid");
    const loadingEl = document.getElementById("venue-schedule-loading");
    const emptyEl = document.getElementById("venue-schedule-empty");
    const slotWarning = document.getElementById("venue-slot-warning");
    const errorSummary = document.getElementById("form-error-summary");
    const submitBtn = form.querySelector('button[type="submit"]');

    const editingEventPk = form.dataset.editingEventPk || "";
    const selectedSlots = new Set();
    let latestSlots = [];

    const STATUS_BADGE = {
        free: { class: "bg-success", label: "Available" },
        partial: { class: "bg-warning text-dark", label: "Partial" },
        full: { class: "bg-danger", label: "Full" },
    };

    const STATUS_BTN = {
        free: "btn-outline-success",
        partial: "btn-outline-warning",
        full: "btn-outline-secondary",
    };

    const PLACEHOLDER_ROW =
        '<tr><td colspan="5" class="text-center text-muted py-4">Select a venue and date to load availability.</td></tr>';

    function pad(n) {
        return String(n).padStart(2, "0");
    }

    function plannedGuests() {
        const value = parseInt(maxPlayersInput && maxPlayersInput.value, 10);
        return Number.isFinite(value) && value > 0 ? value : 4;
    }

    function isoToTimeValue(isoString) {
        const d = new Date(isoString);
        return pad(d.getHours()) + ":" + pad(d.getMinutes());
    }

    function setFieldActive(input, active) {
        if (!input) return;
        input.disabled = !active;
        input.required = active;
        if (!active) {
            input.removeAttribute("required");
        }
    }

    function setScheduleMode(venueMode) {
        setFieldActive(eventDateInput, venueMode);
        setFieldActive(startTimeInput, venueMode);
        setFieldActive(endTimeInput, venueMode);
        setFieldActive(dateTimeInput, !venueMode);
        setFieldActive(endDateTimeInput, !venueMode);
        if (playersOutsideVenue) {
            playersOutsideVenue.classList.toggle("d-none", venueMode);
        }
    }

    function syncHiddenSlots() {
        if (!slotsHiddenInput) return;
        const ordered = Array.from(selectedSlots).sort();
        slotsHiddenInput.value = ordered.join(",");
    }

    function loadInitialSlots() {
        if (!slotsHiddenInput || !slotsHiddenInput.value) return;
        slotsHiddenInput.value.split(",").forEach((iso) => {
            const trimmed = iso.trim();
            if (trimmed) selectedSlots.add(trimmed);
        });
    }

    function orderedSelectedMeta() {
        return Array.from(selectedSlots)
            .map((startIso) => latestSlots.find((s) => s.start === startIso))
            .filter(Boolean)
            .sort((a, b) => new Date(a.start) - new Date(b.start));
    }

    /** Fill every bookable hour between the earliest and latest selected slot. */
    function expandSelectionToRange() {
        const selected = orderedSelectedMeta();
        if (!selected.length) return;
        const minTime = new Date(selected[0].start).getTime();
        const maxTime = new Date(selected[selected.length - 1].start).getTime();
        latestSlots.forEach((slot) => {
            const slotTime = new Date(slot.start).getTime();
            if (
                slot.bookable !== false &&
                slotTime >= minTime &&
                slotTime <= maxTime
            ) {
                selectedSlots.add(slot.start);
            }
        });
    }

    function updateSlotWarning() {
        if (!slotWarning) return;
        const meta = orderedSelectedMeta();
        if (!meta.length) {
            slotWarning.classList.add("d-none");
            slotWarning.textContent = "";
            return;
        }
        slotWarning.textContent = `${meta.length} hour(s) selected — one table for the full block.`;
        slotWarning.classList.remove("d-none");
    }

    function markScheduleFieldsFilled(filled) {
        [startTimeInput, endTimeInput].forEach((input) => {
            if (!input) return;
            input.classList.toggle("venue-schedule-filled", filled);
        });
    }

    function pushTimeInputValue(input, value) {
        if (!input) return;
        input.value = value;
        input.classList.remove("is-invalid");
        input.dispatchEvent(new Event("input", { bubbles: true }));
    }

    function applyMergedRange(metaList) {
        if (!metaList.length) return;
        const first = metaList[0];
        const last = metaList[metaList.length - 1];
        pushTimeInputValue(startTimeInput, isoToTimeValue(first.start));
        pushTimeInputValue(endTimeInput, isoToTimeValue(last.end));
        if (eventDateInput) {
            eventDateInput.classList.remove("is-invalid");
        }
        markScheduleFieldsFilled(true);
        syncHiddenSlots();
        updateSlotWarning();
    }

    function refreshRowHighlights() {
        hourGridBody.querySelectorAll("tr[data-slot-start]").forEach((row) => {
            const start = row.dataset.slotStart;
            const isSelected = selectedSlots.has(start);
            row.classList.toggle("table-active", isSelected);
            const btn = row.querySelector(".select-slot-btn");
            if (btn) {
                btn.textContent = isSelected ? "Remove" : "Select";
                btn.setAttribute("aria-pressed", isSelected ? "true" : "false");
            }
        });
    }

    function toggleSlot(slot) {
        if (!slot.bookable) return;
        if (selectedSlots.has(slot.start)) {
            selectedSlots.delete(slot.start);
        } else {
            selectedSlots.add(slot.start);
            expandSelectionToRange();
        }
        refreshRowHighlights();
        const meta = orderedSelectedMeta();
        if (meta.length) {
            applyMergedRange(meta);
        } else {
            markScheduleFieldsFilled(false);
            syncHiddenSlots();
            updateSlotWarning();
        }
    }

    function buildAvailabilityUrl(venueId, dateStr) {
        let url = `/venues/${venueId}/availability/?date=${encodeURIComponent(dateStr)}`;
        url += `&guests=${encodeURIComponent(plannedGuests())}`;
        if (editingEventPk) {
            url += `&exclude_event=${encodeURIComponent(editingEventPk)}`;
        }
        return url;
    }

    function renderSlots(slots) {
        latestSlots = slots || [];
        hourGridBody.innerHTML = "";
        if (!slots.length) {
            emptyEl.textContent = "No bookable hours on this date.";
            emptyEl.classList.remove("d-none");
            hourGridBody.innerHTML =
                '<tr><td colspan="5" class="text-center text-muted py-4">No bookable hours on this date.</td></tr>';
            return;
        }
        emptyEl.classList.add("d-none");

        slots.forEach((slot) => {
            const badge = STATUS_BADGE[slot.status] || STATUS_BADGE.full;
            const row = document.createElement("tr");
            row.dataset.slotStart = slot.start;

            if (slot.status === "full") {
                row.classList.add("table-secondary");
            }
            if (selectedSlots.has(slot.start)) {
                row.classList.add("table-active");
            }

            const canSelect = slot.bookable !== false;
            const guestsLabel = `${slot.guests_booked} / ${slot.venue_capacity} booked`;

            row.innerHTML = `
                <td class="fw-semibold">${slot.label}</td>
                <td>${slot.free_tables} / ${slot.total_tables} tables</td>
                <td>${guestsLabel}<div class="small text-muted">${slot.guests_remaining} seats left</div></td>
                <td class="text-center">
                    <span class="badge rounded-pill ${badge.class}">${badge.label}</span>
                </td>
                <td class="text-end">
                    <button type="button" class="btn btn-sm ${STATUS_BTN[slot.status] || STATUS_BTN.full} select-slot-btn" ${canSelect ? "" : "disabled"} aria-pressed="${selectedSlots.has(slot.start) ? "true" : "false"}">
                        ${selectedSlots.has(slot.start) ? "Remove" : "Select"}
                    </button>
                </td>
            `;

            if (canSelect) {
                const selectBtn = row.querySelector(".select-slot-btn");
                selectBtn.addEventListener("mousedown", (e) => {
                    e.preventDefault();
                    toggleSlot(slot);
                });
            }

            hourGridBody.appendChild(row);
        });
        updateSlotWarning();
    }

    async function loadAvailability() {
        const venueId = venueSelect.value;
        const dateStr = eventDateInput && eventDateInput.value;
        if (!venueId || !dateStr) {
            hourGridBody.innerHTML = PLACEHOLDER_ROW;
            emptyEl.classList.add("d-none");
            return;
        }

        loadingEl.classList.remove("d-none");
        emptyEl.classList.add("d-none");

        try {
            const response = await fetch(buildAvailabilityUrl(venueId, dateStr), {
                headers: { Accept: "application/json" },
                credentials: "same-origin",
            });
            if (!response.ok) {
                throw new Error("Failed to load availability");
            }
            const data = await response.json();
            renderSlots(data.slots || []);
        } catch (err) {
            hourGridBody.innerHTML =
                '<tr><td colspan="5" class="text-center text-danger py-4">Could not load availability. Try again.</td></tr>';
            emptyEl.classList.add("d-none");
        } finally {
            loadingEl.classList.add("d-none");
        }
    }

    function defaultVenueTimesIfEmpty() {
        if (startTimeInput && !startTimeInput.value) {
            startTimeInput.value = "14:00";
        }
        if (endTimeInput && !endTimeInput.value) {
            endTimeInput.value = "16:00";
        }
    }

    function selectedVenueName() {
        if (!venueSelect || !venueSelect.value) return "";
        const opt = venueSelect.options[venueSelect.selectedIndex];
        return opt ? opt.text.trim() : "";
    }

    async function fetchVenueGames(venueId) {
        const venueName = selectedVenueName();
        if (!venueId) {
            document.dispatchEvent(
                new CustomEvent("venue-games-changed", {
                    detail: { venueId: null, games: [], venueName: "" },
                })
            );
            return;
        }
        try {
            const res = await fetch("/api/venues/" + venueId + "/games/", {
                headers: { Accept: "application/json" },
            });
            if (!res.ok) return;
            const games = await res.json();
            document.dispatchEvent(
                new CustomEvent("venue-games-changed", {
                    detail: { venueId: venueId, games: games, venueName: venueName },
                })
            );
        } catch (_e) {
            document.dispatchEvent(
                new CustomEvent("venue-games-changed", {
                    detail: { venueId: venueId, games: [], venueName: venueName },
                })
            );
        }
    }

    function toggleVenueMode() {
        const hasVenue = venueSelect && venueSelect.value;
        if (hasVenue) {
            locationWrapper.classList.add("d-none");
            schedulePanel.classList.remove("d-none");
            independentFields.classList.add("d-none");
            setScheduleMode(true);
            defaultVenueTimesIfEmpty();
            loadAvailability();
            fetchVenueGames(venueSelect.value);
        } else {
            locationWrapper.classList.remove("d-none");
            schedulePanel.classList.add("d-none");
            independentFields.classList.remove("d-none");
            setScheduleMode(false);
            selectedSlots.clear();
            syncHiddenSlots();
            hourGridBody.innerHTML = PLACEHOLDER_ROW;
            fetchVenueGames(null);
        }
    }

    form.addEventListener("submit", function (event) {
        const venueMode = venueSelect && venueSelect.value;
        setScheduleMode(!!venueMode);

        if (venueMode) {
            const meta = orderedSelectedMeta();
            if (meta.length) {
                applyMergedRange(meta);
            }
            syncHiddenSlots();
            if (!eventDateInput.value || !startTimeInput.value || !endTimeInput.value) {
                event.preventDefault();
                if (!eventDateInput.value) eventDateInput.classList.add("is-invalid");
                if (!startTimeInput.value) startTimeInput.classList.add("is-invalid");
                if (!endTimeInput.value) endTimeInput.classList.add("is-invalid");
                return;
            }
        }

        if (!form.checkValidity()) {
            event.preventDefault();
            form.reportValidity();
            return;
        }

        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML =
                '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Saving…';
        }
    });

    if (venueSelect) {
        venueSelect.addEventListener("change", () => {
            selectedSlots.clear();
            syncHiddenSlots();
            toggleVenueMode();
        });
    }
    if (eventDateInput) {
        eventDateInput.addEventListener("change", () => {
            selectedSlots.clear();
            syncHiddenSlots();
            loadAvailability();
        });
    }
    if (maxPlayersInput) {
        let guestTimer;
        maxPlayersInput.addEventListener("input", () => {
            clearTimeout(guestTimer);
            guestTimer = setTimeout(loadAvailability, 500);
        });
    }

    if (eventDateInput && !eventDateInput.value) {
        const today = new Date();
        eventDateInput.value =
            today.getFullYear() +
            "-" +
            pad(today.getMonth() + 1) +
            "-" +
            pad(today.getDate());
    }

    loadInitialSlots();
    toggleVenueMode();

    if (errorSummary) {
        errorSummary.scrollIntoView({ behavior: "smooth", block: "start" });
    }
})();
