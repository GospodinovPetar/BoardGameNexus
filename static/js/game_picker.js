(function () {
    function getCookie(name) {
        const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
        return match ? decodeURIComponent(match[2]) : "";
    }

    class GamePicker {
        constructor(root) {
            this.root = root;
            this.mode = root.dataset.mode || "full";
            this.inputName = root.dataset.inputName || "games";
            this.searchUrl = root.dataset.searchUrl;
            this.ensureUrl = root.dataset.ensureUrl;
            this.csrfToken = root.dataset.csrfToken || getCookie("csrftoken");
            this.placeholderUrl = root.dataset.placeholderUrl || "";
            this.searchInput = root.querySelector(".game-picker-search");
            this.dropdown = root.querySelector(".game-picker-dropdown");
            this.chips = root.querySelector(".game-picker-chips");
            this.hiddenHost = root.querySelector(".game-picker-hidden-inputs");
            this.hint = root.querySelector(".game-picker-hint");
            this.loadingEl = root.querySelector(".game-picker-loading");
            this.countEl = root.querySelector(".game-picker-count");
            this.modeBadge = root.querySelector(".game-picker-mode-badge");
            this.staleHintEl = root.querySelector(".game-picker-stale-hint");
            this.selected = new Map();
            this.allowedCatalog = [];
            this.debounceTimer = null;
            this._bind();
            this._loadInitial();
            this._renderEmptyState();
            this._updateCount();
        }

        _bind() {
            this.searchInput.addEventListener("input", () => {
                clearTimeout(this.debounceTimer);
                this.debounceTimer = setTimeout(() => this._onSearch(), 280);
            });
            this.searchInput.addEventListener("focus", () => {
                this.searchInput.setAttribute("aria-expanded", "true");
                if (this.mode === "venue_catalog") {
                    this._showCatalogResults(this.searchInput.value);
                } else if (this.searchInput.value.trim().length >= 2) {
                    this._onSearch();
                }
            });
            this.searchInput.addEventListener("keydown", (e) => {
                if (e.key === "Escape") this._hideDropdown();
            });
            document.addEventListener("click", (e) => {
                if (!this.root.contains(e.target)) {
                    this._hideDropdown();
                    this.searchInput.setAttribute("aria-expanded", "false");
                }
            });
        }

        _setLoading(on) {
            if (this.loadingEl) {
                this.loadingEl.classList.toggle("d-none", !on);
            }
        }

        _loadInitial() {
            try {
                const initial = JSON.parse(this.root.dataset.initialGames || "[]");
                initial.forEach((g) => this._addChip(g, false));
            } catch (_e) {
                /* ignore */
            }
            try {
                this.allowedCatalog = JSON.parse(this.root.dataset.allowedGames || "[]");
            } catch (_e) {
                this.allowedCatalog = [];
            }
            if (this.selected.size) {
                this._clearEmptyState();
            }
        }

        setMode(mode, allowedGames) {
            this.mode = mode;
            this.allowedCatalog = allowedGames || [];
            this.root.dataset.mode = mode;
            if (this.hint) {
                this.hint.textContent =
                    mode === "venue_catalog"
                        ? "Pick from this venue’s library — search filters the list below."
                        : "Search BoardGameGeek’s catalog and add every game you plan to play.";
            }
            if (this.modeBadge) {
                this.modeBadge.textContent = mode === "venue_catalog" ? "Venue" : "BGG";
            }
            this.searchInput.placeholder =
                mode === "venue_catalog"
                    ? "Filter venue games…"
                    : "Search e.g. Catan, Wingspan…";
            const allowedIds = new Set(this.allowedCatalog.map((g) => String(g.id)));
            Array.from(this.selected.keys()).forEach((id) => {
                if (mode === "venue_catalog" && !allowedIds.has(String(id))) {
                    this.removeGame(id);
                }
            });
            this.searchInput.value = "";
            this._hideDropdown();
            if (!this.selected.size) this._renderEmptyState();
        }

        async _onSearch() {
            const q = this.searchInput.value.trim();
            if (this.mode === "venue_catalog") {
                this._showCatalogResults(q);
                return;
            }
            if (q.length < 2) {
                this._hideDropdown();
                return;
            }
            this._setLoading(true);
            try {
                const res = await fetch(
                    this.searchUrl + "?q=" + encodeURIComponent(q),
                    { headers: { Accept: "application/json" } }
                );
                const data = await res.json().catch(() => ({}));
                if (!res.ok) {
                    const detail =
                        (data && data.detail) ||
                        "Search unavailable. Check BGG_API_KEY in .env.";
                    this._showDropdownMessage(detail);
                    return;
                }
                if (res.headers.get("X-BGG-Cache") === "stale") {
                    this._showStaleHint(true);
                } else {
                    this._showStaleHint(false);
                }
                this._renderBggResults(data);
            } catch (_e) {
                this._showDropdownMessage("Search failed. Check your connection.");
            } finally {
                this._setLoading(false);
            }
        }

        _showCatalogResults(query) {
            const q = query.toLowerCase();
            const filtered = this.allowedCatalog.filter(
                (g) => !q || (g.title || "").toLowerCase().includes(q)
            );
            if (!this.allowedCatalog.length) {
                this._showDropdownMessage(
                    "This venue has no games yet. Add games when editing the venue."
                );
                return;
            }
            if (!filtered.length) {
                this._showDropdownMessage("No matching games in this venue’s catalog.");
                return;
            }
            this._renderCatalogResults(filtered);
        }

        _thumbHtml(imageUrl, alt) {
            if (imageUrl) {
                return (
                    '<img class="game-picker-result-thumb" src="' +
                    this._escapeAttr(imageUrl) +
                    '" alt="" loading="lazy">'
                );
            }
            return (
                '<span class="game-picker-result-thumb-placeholder" aria-hidden="true">' +
                '<i class="bi bi-box-seam-fill"></i></span>'
            );
        }

        _resultButton(item, innerHtml, onClick) {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "game-picker-result";
            btn.setAttribute("role", "option");
            btn.innerHTML = innerHtml;
            btn.addEventListener("click", onClick);
            return btn;
        }

        _renderBggResults(results) {
            this.dropdown.innerHTML = "";
            if (!results.length) {
                this._showDropdownMessage("No games found — try another spelling.");
                return;
            }
            results.forEach((item) => {
                const year = item.year_published
                    ? '<span class="game-picker-result-meta">' + item.year_published + "</span>"
                    : '<span class="game-picker-result-meta">BoardGameGeek</span>';
                const inner =
                    this._thumbHtml(null, item.title) +
                    '<span class="game-picker-result-body">' +
                    '<span class="game-picker-result-title">' +
                    this._escape(item.title) +
                    "</span>" +
                    year +
                    "</span>" +
                    '<span class="game-picker-result-add" aria-hidden="true"><i class="bi bi-plus-lg"></i></span>';
                const btn = this._resultButton(item, inner, () => this._selectBgg(item));
                this.dropdown.appendChild(btn);
            });
            this._showDropdown();
        }

        _renderCatalogResults(games) {
            this.dropdown.innerHTML = "";
            let added = 0;
            games.forEach((g) => {
                if (this.selected.has(String(g.id))) return;
                added += 1;
                const meta = g.year_published
                    ? String(g.year_published)
                    : "At this venue";
                const inner =
                    this._thumbHtml(g.image_url, g.title) +
                    '<span class="game-picker-result-body">' +
                    '<span class="game-picker-result-title">' +
                    this._escape(g.title) +
                    "</span>" +
                    '<span class="game-picker-result-meta">' +
                    this._escape(meta) +
                    "</span></span>" +
                    '<span class="game-picker-result-add" aria-hidden="true"><i class="bi bi-plus-lg"></i></span>';
                const btn = this._resultButton(g, inner, () => this._addChip(g, true));
                this.dropdown.appendChild(btn);
            });
            if (!added) {
                this._showDropdownMessage("All venue games are already selected.");
                return;
            }
            this._showDropdown();
        }

        _showDropdownMessage(text) {
            this.dropdown.innerHTML =
                '<div class="game-picker-dropdown-message">' +
                '<i class="bi bi-info-circle d-block mb-2 fs-5 opacity-50"></i>' +
                this._escape(text) +
                "</div>";
            this._showDropdown();
        }

        _showDropdown() {
            this.dropdown.classList.remove("d-none");
            this.searchInput.setAttribute("aria-expanded", "true");
        }

        _hideDropdown() {
            this.dropdown.classList.add("d-none");
            this.searchInput.setAttribute("aria-expanded", "false");
        }

        _showStaleHint(on) {
            if (!this.staleHintEl) return;
            this.staleHintEl.classList.toggle("d-none", !on);
        }

        async addByBggId(bggId) {
            if (this.mode !== "full") return;
            const existing = Array.from(this.selected.values()).find(
                (g) => String(g.bgg_id) === String(bggId)
            );
            if (existing) return;
            await this._selectBgg({ bgg_id: Number(bggId) });
        }

        addLocalGame(game) {
            if (!game || !game.id) return;
            this._addChip(
                {
                    id: game.id,
                    bgg_id: game.bgg_id,
                    title: game.title,
                    image_url: game.image_url || "",
                    year_published: game.year_published,
                },
                true
            );
        }

        async _selectBgg(item) {
            if (item.id) {
                this.addLocalGame(item);
                return;
            }
            const existing = Array.from(this.selected.values()).find(
                (g) => item.bgg_id && String(g.bgg_id) === String(item.bgg_id)
            );
            if (existing) return;
            this._hideDropdown();
            this.searchInput.value = "";
            this._setLoading(true);
            try {
                const res = await fetch(this.ensureUrl, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Accept: "application/json",
                        "X-CSRFToken": this.csrfToken,
                    },
                    body: JSON.stringify({ bgg_ids: [item.bgg_id] }),
                });
                const data = await res.json().catch(() => ({}));
                if (!res.ok) {
                    this._showDropdownMessage(
                        (data && data.detail) || "Could not add this game. Try again."
                    );
                    return;
                }
                if (data[0]) {
                    this._addChip(
                        {
                            id: data[0].id,
                            bgg_id: data[0].bgg_id,
                            title: data[0].title,
                            image_url: data[0].image_url,
                            year_published: data[0].year_published,
                        },
                        true
                    );
                }
            } catch (_e) {
                this._showDropdownMessage("Could not add game. Check your connection.");
            } finally {
                this._setLoading(false);
            }
        }

        _renderEmptyState() {
            if (this.chips.querySelector(".game-picker-empty")) return;
            this.chips.innerHTML =
                '<div class="game-picker-empty">' +
                '<i class="bi bi-collection"></i>' +
                "<span>No games selected yet</span>" +
                "<span class=\"small mt-1\">Use search above to add titles</span>" +
                "</div>";
        }

        _clearEmptyState() {
            const empty = this.chips.querySelector(".game-picker-empty");
            if (empty) empty.remove();
        }

        _addChip(game, syncHidden) {
            const id = String(game.id);
            if (this.selected.has(id)) return;
            if (this.mode === "venue_catalog") {
                const allowed = new Set(this.allowedCatalog.map((g) => String(g.id)));
                if (!allowed.has(id)) return;
            }
            this._clearEmptyState();
            this.selected.set(id, game);

            const card = document.createElement("div");
            card.className = "game-picker-chip-card";
            card.dataset.gameId = id;

            const thumb = game.image_url
                ? '<img class="game-picker-chip-thumb" src="' +
                  this._escapeAttr(game.image_url) +
                  '" alt="">'
                : '<span class="game-picker-chip-thumb-placeholder"><i class="bi bi-box-seam-fill"></i></span>';

            const meta = game.year_published
                ? String(game.year_published)
                : game.bgg_id
                  ? "BGG #" + game.bgg_id
                  : "";

            card.innerHTML =
                thumb +
                '<div class="game-picker-chip-body">' +
                '<div class="game-picker-chip-title">' +
                this._escape(game.title) +
                "</div>" +
                (meta
                    ? '<div class="game-picker-chip-meta">' + this._escape(meta) + "</div>"
                    : "") +
                "</div>" +
                '<button type="button" class="game-picker-chip-remove" aria-label="Remove ' +
                this._escape(game.title) +
                '"><i class="bi bi-x-lg"></i></button>';

            card.querySelector(".game-picker-chip-remove").addEventListener("click", () =>
                this.removeGame(id)
            );
            this.chips.appendChild(card);
            if (syncHidden) this._syncHidden();
            this._updateCount();
            this._hideDropdown();
        }

        removeGame(id) {
            id = String(id);
            this.selected.delete(id);
            const chip = this.chips.querySelector('[data-game-id="' + id + '"]');
            if (chip) chip.remove();
            this._syncHidden();
            this._updateCount();
            if (!this.selected.size) this._renderEmptyState();
        }

        _updateCount() {
            if (!this.countEl) return;
            const n = this.selected.size;
            this.countEl.textContent = String(n);
            this.countEl.classList.toggle("is-zero", n === 0);
        }

        _syncHidden() {
            this.hiddenHost.innerHTML = "";
            this.selected.forEach((_game, id) => {
                const input = document.createElement("input");
                input.type = "hidden";
                input.name = this.inputName;
                input.value = id;
                this.hiddenHost.appendChild(input);
            });
        }

        _escape(text) {
            const div = document.createElement("div");
            div.textContent = text == null ? "" : String(text);
            return div.innerHTML;
        }

        _escapeAttr(text) {
            return String(text == null ? "" : text)
                .replace(/&/g, "&amp;")
                .replace(/"/g, "&quot;")
                .replace(/</g, "&lt;");
        }
    }

    const registry = new Map();

    function initPicker(root) {
        if (!root || registry.has(root.id)) return registry.get(root.id);
        const picker = new GamePicker(root);
        registry.set(root.id, picker);
        return picker;
    }

    document.querySelectorAll(".game-picker").forEach((root) => initPicker(root));

    function bindRecommendedAddButtons(root) {
        if (!root) return;
        root.querySelectorAll(".recommended-add-btn").forEach((btn) => {
            if (btn.dataset.bound === "1") return;
            btn.dataset.bound = "1";
            btn.addEventListener("click", () => {
                const picker = registry.get("event-games-picker");
                if (!picker) return;
                const localId = btn.dataset.localId;
                if (localId) {
                    picker.addLocalGame({
                        id: localId,
                        bgg_id: btn.dataset.bggId ? Number(btn.dataset.bggId) : undefined,
                        title: btn.dataset.title || "",
                        image_url: btn.dataset.imageUrl || "",
                        year_published: btn.dataset.yearPublished
                            ? Number(btn.dataset.yearPublished)
                            : undefined,
                    });
                    return;
                }
                const bggId = btn.dataset.bggId;
                if (bggId) picker.addByBggId(bggId);
            });
        });
    }

    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text == null ? "" : String(text);
        return div.innerHTML;
    }

    function escapeAttr(text) {
        return String(text == null ? "" : text)
            .replace(/&/g, "&amp;")
            .replace(/"/g, "&quot;")
            .replace(/</g, "&lt;");
    }

    function renderRecommendedCard(item, placeholderUrl) {
        const img = item.image_url
            ? '<img src="' + escapeAttr(item.image_url) + '" class="rounded mb-2 recommended-picker-thumb" alt="">'
            : '<img src="' + escapeAttr(placeholderUrl) + '" class="rounded mb-2 recommended-picker-thumb" alt="">';
        const rating = item.bgg_rating
            ? '<div class="small text-warning"><i class="bi bi-star-fill"></i> ' + item.bgg_rating + "</div>"
            : "";
        const bggLink = item.bgg_url
            ? '<a href="' +
              escapeAttr(item.bgg_url) +
              '" target="_blank" rel="noopener noreferrer" class="btn btn-sm btn-outline-secondary">BGG</a>'
            : "";
        return (
            '<div class="col"><div class="card bg-dark text-white border border-warning border-opacity-25 h-100">' +
            '<div class="card-body p-2 d-flex flex-column">' +
            img +
            '<div class="small fw-semibold text-truncate" title="' +
            escapeAttr(item.title) +
            '">' +
            escapeHtml(item.title) +
            "</div>" +
            rating +
            '<div class="mt-auto d-flex flex-column gap-1 pt-2">' +
            '<button type="button" class="btn btn-sm btn-warning recommended-add-btn"' +
            ' data-bgg-id="' +
            item.bgg_id +
            '"' +
            (item.local_id ? ' data-local-id="' + item.local_id + '"' : "") +
            ' data-title="' +
            escapeAttr(item.title) +
            '"' +
            ' data-image-url="' +
            escapeAttr(item.image_url || "") +
            '"' +
            (item.year_published
                ? ' data-year-published="' + item.year_published + '"'
                : "") +
            '><i class="bi bi-plus-lg me-1"></i>Add</button>' +
            bggLink +
            "</div></div></div></div>"
        );
    }

    async function refreshEventRecommended(venueId, venueName) {
        const section = document.getElementById("event-recommended-games");
        if (!section) return;

        const placeholderUrl = section.dataset.placeholderUrl || "";
        const globalUrl = section.dataset.globalRecommendedUrl || "/api/games/recommended/";
        const grid = section.querySelector(".recommended-games-picker-grid");
        const emptyEl = section.querySelector(".recommended-games-picker-empty");
        const titleEl = section.querySelector(".recommended-games-picker-title");
        const subtitleEl = section.querySelector(".recommended-games-picker-subtitle");
        const countEl = section.querySelector(".recommended-games-picker-count");

        let url = globalUrl;
        if (venueId) {
            url = "/api/venues/" + encodeURIComponent(venueId) + "/recommended-games/";
        }

        try {
            const res = await fetch(url, { headers: { Accept: "application/json" } });
            const data = await res.json().catch(() => []);
            if (!res.ok) {
                section.classList.add("d-none");
                return;
            }

            const items = Array.isArray(data) ? data : [];
            if (venueId) {
                section.dataset.scope = "venue";
                section.dataset.venueName = venueName || "";
                if (titleEl) {
                    titleEl.textContent = venueName
                        ? "Top picks at " + venueName
                        : "Top picks at this venue";
                }
                if (subtitleEl) {
                    subtitleEl.textContent =
                        "Highest-rated games from this venue’s library — click Add to include them in your event.";
                }
            } else {
                section.dataset.scope = "global";
                if (titleEl) titleEl.textContent = "Recommended on BoardGameGeek";
                if (subtitleEl) {
                    subtitleEl.textContent =
                        "Highest-ranked board games from BGG — click Add to include them in this event.";
                }
            }

            if (countEl) countEl.textContent = "Top " + items.length;

            if (grid) {
                grid.innerHTML = items.map((item) => renderRecommendedCard(item, placeholderUrl)).join("");
                bindRecommendedAddButtons(section);
            }

            const showEmpty = venueId && items.length === 0;
            if (emptyEl) emptyEl.classList.toggle("d-none", !showEmpty);
            section.classList.toggle("d-none", !venueId && items.length === 0);
        } catch (_e) {
            if (!venueId) section.classList.add("d-none");
        }
    }

    document.addEventListener("venue-games-changed", (e) => {
        const picker = registry.get("event-games-picker");
        const detail = e.detail || {};
        if (!picker) return;
        if (detail.venueId) {
            picker.setMode("venue_catalog", detail.games || []);
            refreshEventRecommended(detail.venueId, detail.venueName || "");
        } else {
            picker.setMode("full", []);
            refreshEventRecommended(null, "");
        }
    });

    const initialRecommended = document.getElementById("event-recommended-games");
    bindRecommendedAddButtons(initialRecommended);

    window.BoardGameNexus = window.BoardGameNexus || {};
    window.BoardGameNexus.initGamePicker = initPicker;
    window.BoardGameNexus.getGamePicker = (id) => registry.get(id);
})();
