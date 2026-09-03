/* ==========================================================
   API URLS
========================================================== */

const AUTHORITY_API_URL =
    "/api/v1/manager/projects/";

const GRID_API_URL =
    "/api/v1/manager/grids/";

const REVIEW_API_URL =
    "/api/v1/manager/reviews/";


/* ==========================================================
   GLOBAL STATE
========================================================== */

window.managerAuthorities = [];

window.managerGrids = [];

window.managerReviews = [];

window.managerFilteredGrids = [];

window.managerFilteredMapGrids = [];

window.managerFilters = {
    authority: "",
    status: "",
    user: ""
};

window.managerMapRenderMode = "status";

window.managerMap = null;

window.managerMapView = null;

window.managerGraphicsLayer = null;

window.managerGraphicClass = null;


/* ==========================================================
   CSRF
========================================================== */

function getCsrfToken() {

    const name = "csrftoken=";

    const cookies =
        document.cookie.split(";");

    for (let cookie of cookies) {

        cookie = cookie.trim();

        if (cookie.startsWith(name)) {

            return decodeURIComponent(
                cookie.substring(name.length)
            );

        }

    }

    return "";

}


/* ==========================================================
   GENERIC API
========================================================== */

async function fetchApi(url) {

    const startTime =
        performance.now();

    console.log(
        `[API] Loading: ${url}`
    );


    const response =
        await fetch(
            url,
            {
                headers: {
                    "Accept":
                        "application/json"
                },

                credentials:
                    "same-origin"
            }
        );


    if (!response.ok) {

        throw new Error(
            `HTTP ${response.status} - ${url}`
        );

    }


    const data =
        await response.json();


    const elapsed =
        performance.now() -
        startTime;


    console.log(
        `[API] ${url} loaded in ${elapsed.toFixed(0)}ms`
    );


    /*
     * DRF pagination.
     */

    if (Array.isArray(data)) {

        return data;

    }


    if (Array.isArray(data.results)) {

        return data.results;

    }


    if (Array.isArray(data.data)) {

        return data.data;

    }


    console.warn(
        `[API] Unexpected response format from ${url}:`,
        data
    );


    return [];

}


/* ==========================================================
   DASHBOARD INITIALIZATION
========================================================== */

async function loadDashboard() {

    try {

        console.log(
            "[Dashboard] Loading authorities..."
        );


        /*
         * IMPORTANT:
         *
         * We intentionally DO NOT load all grids
         * here.
         *
         * This prevents the large Grid API response
         * from consuming Render's memory.
         */

        window.managerAuthorities =
            await fetchApi(
                AUTHORITY_API_URL
            );


        console.log(
            "[Dashboard] Authorities loaded:",
            window.managerAuthorities.length
        );


        /*
         * Create filter controls.
         *
         * Authority options are populated from
         * the Authority API, not from grids.
         */

        createFilterNavbar();


        /*
         * Default Authority.
         */

        const selected =
            setDefaultAuthorityFilter(
                "Richmondshire"
            );


        if (!selected) {

            console.warn(
                "[Dashboard] Richmondshire not found."
            );


            /*
             * If Richmondshire doesn't exist,
             * leave the authority filter empty.
             */

            window.managerFilters.authority =
                "";

        }


        /*
         * Load only the selected authority.
         */

        await loadFilteredDashboard();


        console.log(
            "[Dashboard] Initialization complete."
        );

    }
    catch (error) {

        console.error(
            "[Dashboard] Initialization failed:",
            error
        );

    }

}


/* ==========================================================
   FILTER NAVBAR
========================================================== */

function createFilterNavbar() {

    const filterBar =
        document.getElementById(
            "manager-filter-bar"
        );


    if (!filterBar) {

        console.warn(
            "[Filters] #manager-filter-bar not found."
        );

        return;

    }


    const authoritySelect =
        document.getElementById(
            "filter-authority"
        );

    const statusSelect =
        document.getElementById(
            "filter-status"
        );

    const userSelect =
        document.getElementById(
            "filter-user"
        );

    const renderSelect =
        document.getElementById(
            "map-render-mode"
        );

    const resetButton =
        document.getElementById(
            "reset-filters"
        );


    /*
     * Populate Authority first.
     */

    populateAuthorityOptions();


    /*
     * Other options will be populated
     * after the selected authority's grids
     * have been loaded.
     */


    /* ======================================================
       AUTHORITY
    ====================================================== */

    if (authoritySelect) {

        authoritySelect.addEventListener(
            "calciteSelectChange",
            handleFiltersChanged
        );

    }


    /* ======================================================
       STATUS
    ====================================================== */

    if (statusSelect) {

        statusSelect.addEventListener(
            "calciteSelectChange",
            handleFiltersChanged
        );

    }


    /* ======================================================
       USER
    ====================================================== */

    if (userSelect) {

        userSelect.addEventListener(
            "calciteSelectChange",
            handleFiltersChanged
        );

    }


    /* ======================================================
       MAP RENDER MODE
    ====================================================== */

    if (renderSelect) {

        renderSelect.addEventListener(
            "calciteSelectChange",
            handleMapRenderModeChanged
        );


        renderSelect.value =
            window.managerMapRenderMode ||
            "status";

    }


    /* ======================================================
       RESET
    ====================================================== */

    if (resetButton) {

        resetButton.addEventListener(
            "click",
            resetFilters
        );

    }


    console.log(
        "[Filters] Filter navbar initialized."
    );

}


/* ==========================================================
   AUTHORITY OPTIONS
========================================================== */

function populateAuthorityOptions() {

    const authoritySelect =
        document.getElementById(
            "filter-authority"
        );


    if (!authoritySelect) {

        return;

    }


    const currentAuthority =
        window.managerFilters.authority;


    authoritySelect.innerHTML = `

        <calcite-option value="">
            All Authorities
        </calcite-option>

    `;


    const authorities =
        [...window.managerAuthorities]
            .sort(
                (a, b) =>
                    String(
                        a.name || ""
                    ).localeCompare(
                        String(
                            b.name || ""
                        )
                    )
            );


    authorities.forEach(
        authority => {

            if (
                authority.id === undefined ||
                authority.id === null
            ) {

                return;

            }


            const option =
                document.createElement(
                    "calcite-option"
                );


            option.value =
                String(
                    authority.id
                );


            option.textContent =
                String(
                    authority.name || ""
                );


            authoritySelect.appendChild(
                option
            );

        }
    );


    /*
     * Restore existing selection.
     */

    authoritySelect.value =
        currentAuthority || "";

}


/* ==========================================================
   STATUS OPTIONS
========================================================== */

function populateStatusOptions() {

    const statusSelect =
        document.getElementById(
            "filter-status"
        );


    if (!statusSelect) {

        return;

    }


    const currentStatus =
        window.managerFilters.status;


    const statuses =
        new Map();


    window.managerGrids.forEach(
        grid => {

            if (!grid.status) {

                return;

            }


            const value =
                normalizeStatus(
                    grid.status
                );


            const label =
                grid.status_display ||
                prettifyStatus(
                    value
                );


            statuses.set(
                value,
                label
            );

        }
    );


    statusSelect.innerHTML = `

        <calcite-option value="">
            All Statuses
        </calcite-option>

    `;


    [...statuses.entries()]
        .sort(
            (a, b) =>
                a[1].localeCompare(
                    b[1]
                )
        )
        .forEach(
            ([value, label]) => {

                const option =
                    document.createElement(
                        "calcite-option"
                    );


                option.value =
                    value;


                option.textContent =
                    label;


                statusSelect.appendChild(
                    option
                );

            }
        );


    statusSelect.value =
        currentStatus || "";

}


/* ==========================================================
   USER OPTIONS
========================================================== */

function populateUserOptions() {

    const userSelect =
        document.getElementById(
            "filter-user"
        );


    if (!userSelect) {

        return;

    }


    const currentUser =
        window.managerFilters.user;


    const users =
        new Map();


    window.managerGrids.forEach(
        grid => {

            const id =
                grid.assigned_to_id ??
                grid.assigned_to;


            const name =
                grid.assigned_to_name ??
                grid.assigned_to_name_display;


            if (
                id === undefined &&
                !name
            ) {

                return;

            }


            const key =
                id !== undefined &&
                id !== null
                    ? String(id)
                    : String(name);


            users.set(
                key,
                {
                    id:
                        id !== undefined &&
                        id !== null
                            ? String(id)
                            : String(name),

                    name:
                        name
                            ? String(name)
                            : `User ${id}`
                }
            );

        }
    );


    userSelect.innerHTML = `

        <calcite-option value="">
            All Users
        </calcite-option>

    `;


    [...users.values()]
        .sort(
            (a, b) =>
                a.name.localeCompare(
                    b.name
                )
        )
        .forEach(
            user => {

                const option =
                    document.createElement(
                        "calcite-option"
                    );


                option.value =
                    user.id;


                option.textContent =
                    user.name;


                userSelect.appendChild(
                    option
                );

            }
        );


    userSelect.value =
        currentUser || "";

}


/* ==========================================================
   SET DEFAULT AUTHORITY
========================================================== */

function setDefaultAuthorityFilter(
    authorityName
) {

    const authority =
        window.managerAuthorities.find(
            item =>
                String(
                    item.name || ""
                )
                    .trim()
                    .toLowerCase() ===
                String(
                    authorityName
                )
                    .trim()
                    .toLowerCase()
        );


    if (!authority) {

        return false;

    }


    if (
        authority.id === undefined ||
        authority.id === null
    ) {

        console.warn(
            "[Filters] Authority has no ID:",
            authority
        );

        return false;

    }


    const authorityId =
        String(
            authority.id
        );


    window.managerFilters.authority =
        authorityId;


    const authoritySelect =
        document.getElementById(
            "filter-authority"
        );


    if (authoritySelect) {

        authoritySelect.value =
            authorityId;

    }


    console.log(
        "[Filters] Default authority:",
        {
            name:
                authority.name,

            id:
                authorityId
        }
    );


    return true;

}


/* ==========================================================
   STATUS LABEL
========================================================== */

function prettifyStatus(
    value
) {

    return String(value)
        .replace(
            /_/g,
            " "
        )
        .replace(
            /-/g,
            " "
        )
        .replace(
            /\b\w/g,
            char =>
                char.toUpperCase()
        );

}


/* ==========================================================
   NORMALIZE STATUS
========================================================== */

function normalizeStatus(
    value
) {

    return String(
        value || ""
    )
        .trim()
        .toLowerCase()
        .replace(
            /[\s-]+/g,
            "_"
        );

}


/* ==========================================================
   FILTER CHANGE
========================================================== */

async function handleFiltersChanged(
    event
) {

    const authoritySelect =
        document.getElementById(
            "filter-authority"
        );

    const statusSelect =
        document.getElementById(
            "filter-status"
        );

    const userSelect =
        document.getElementById(
            "filter-user"
        );


    window.managerFilters = {

        authority:
            authoritySelect
                ? String(
                    authoritySelect.value || ""
                )
                : "",

        status:
            statusSelect
                ? normalizeStatus(
                    statusSelect.value
                )
                : "",

        user:
            userSelect
                ? String(
                    userSelect.value || ""
                )
                : ""

    };


    console.log(
        "[Filters] Change:",
        {
            changedControl:
                event.target.id,

            value:
                event.target.value,

            filters:
                window.managerFilters
        }
    );


    await loadFilteredDashboard();

}


/* ==========================================================
   RESET FILTERS
========================================================== */

async function resetFilters() {

    /*
     * Reset to Richmondshire instead of
     * loading every grid.
     */

    window.managerFilters.status =
        "";

    window.managerFilters.user =
        "";


    /*
     * Restore Richmondshire as default.
     */

    setDefaultAuthorityFilter(
        "Richmondshire"
    );


    const statusSelect =
        document.getElementById(
            "filter-status"
        );

    const userSelect =
        document.getElementById(
            "filter-user"
        );


    if (statusSelect) {

        statusSelect.value =
            "";

    }


    if (userSelect) {

        userSelect.value =
            "";

    }


    console.log(
        "[Filters] Reset to Richmondshire"
    );


    await loadFilteredDashboard();

}


/* ==========================================================
   LOAD FILTERED DASHBOARD
========================================================== */

async function loadFilteredDashboard() {

    const authority =
        window.managerFilters.authority;

    const status =
        window.managerFilters.status;

    const user =
        window.managerFilters.user;


    /*
     * --------------------------------------------------------
     * GRID QUERY
     * --------------------------------------------------------
     */

    const gridParams =
        new URLSearchParams();


    if (authority) {

        gridParams.set(
            "authority",
            authority
        );

    }


    if (status) {

        gridParams.set(
            "status",
            status
        );

    }


    if (user) {

        gridParams.set(
            "assigned_to",
            user
        );

    }


    const gridUrl =
        gridParams.toString()
            ? `${GRID_API_URL}?${gridParams.toString()}`
            : GRID_API_URL;


    /*
     * --------------------------------------------------------
     * REVIEW QUERY
     * --------------------------------------------------------
     *
     * Reviews currently support Authority only
     * in your Django ViewSet.
     */

    const reviewParams =
        new URLSearchParams();


    if (authority) {

        reviewParams.set(
            "authority",
            authority
        );

    }


    const reviewUrl =
        reviewParams.toString()
            ? `${REVIEW_API_URL}?${reviewParams.toString()}`
            : REVIEW_API_URL;


    try {

        console.log(
            "[Dashboard] Loading filtered data:",
            {
                gridUrl,
                reviewUrl
            }
        );


        /*
         * Do NOT load grids until the
         * authority is known.
         */

        const [
            grids,
            reviews
        ] = await Promise.all([

            fetchApi(
                gridUrl
            ),

            fetchApi(
                reviewUrl
            )

        ]);


        window.managerGrids =
            grids;

        window.managerReviews =
            reviews;


        window.managerFilteredGrids =
            grids;

        window.managerFilteredMapGrids =
            grids;


        console.log(
            "[Dashboard] Filtered data loaded:",
            {
                grids:
                    grids.length,

                reviews:
                    reviews.length
            }
        );


        /*
         * Build Status/User options from
         * the currently loaded grids only.
         */

        populateStatusOptions();

        populateUserOptions();


        /*
         * Authority table.
         *
         * When an authority is selected, show
         * only that authority.
         */

        const filteredAuthorities =
            getFilteredAuthorities();


        renderSummary(
            filteredAuthorities
        );


        renderAuthorities(
            filteredAuthorities
        );


        /*
         * Grid table.
         */

        renderGrids(
            grids
        );


        /*
         * Reviews.
         */

        renderReviews(
            reviews
        );


        /*
         * Map.
         */

        if (
            window.managerMapView
        ) {

            renderMap(
                grids
            );

        }
        else {

            await loadGridMap();

        }

    }
    catch (error) {

        console.error(
            "[Dashboard] Filtered load failed:",
            error
        );

    }

}


/* ==========================================================
   FILTERED AUTHORITIES
========================================================== */

function getFilteredAuthorities() {

    const authority =
        window.managerFilters.authority;


    /*
     * No Authority selected.
     *
     * This is technically capable of loading all
     * authorities, but the initial dashboard uses
     * Richmondshire.
     */

    if (!authority) {

        return window.managerAuthorities;

    }


    return window.managerAuthorities.filter(
        item =>
            String(
                item.id
            ) ===
            String(
                authority
            )
    );

}


/* ==========================================================
   SUMMARY
========================================================== */

function renderSummary(
    authorities
) {

    const totalAuthorities =
        authorities.length;


    const totalKm =
        authorities.reduce(
            (sum, authority) =>
                sum +
                Number(
                    authority.total_km || 0
                ),
            0
        );


    const completedKm =
        authorities.reduce(
            (sum, authority) =>
                sum +
                Number(
                    authority.total_completed_km ||
                    0
                ),
            0
        );


    const reviewedKm =
        authorities.reduce(
            (sum, authority) =>
                sum +
                Number(
                    authority.km_reviewed || 0
                ),
            0
        );


    const digitizationPercentage =
        totalKm > 0
            ? completedKm /
              totalKm *
              100
            : 0;


    const reviewPercentage =
        totalKm > 0
            ? reviewedKm /
              totalKm *
              100
            : 0;


    const totalAuthoritiesElement =
        document.getElementById(
            "total-authorities"
        );

    const totalKmElement =
        document.getElementById(
            "total-km"
        );

    const completedKmElement =
        document.getElementById(
            "completed-km"
        );

    const reviewedKmElement =
        document.getElementById(
            "reviewed-km"
        );

    const digitizationElement =
        document.getElementById(
            "digitization-percentage"
        );

    const reviewElement =
        document.getElementById(
            "review-percentage"
        );


    if (totalAuthoritiesElement) {

        totalAuthoritiesElement.textContent =
            totalAuthorities;

    }


    if (totalKmElement) {

        totalKmElement.textContent =
            totalKm.toFixed(2);

    }


    if (completedKmElement) {

        completedKmElement.textContent =
            completedKm.toFixed(2);

    }


    if (reviewedKmElement) {

        reviewedKmElement.textContent =
            reviewedKm.toFixed(2);

    }


    if (digitizationElement) {

        digitizationElement.textContent =
            `${digitizationPercentage.toFixed(1)}%`;

    }


    if (reviewElement) {

        reviewElement.textContent =
            `${reviewPercentage.toFixed(1)}%`;

    }

}


/* ==========================================================
   AUTHORITY TABLE
========================================================== */

function renderAuthorities(
    authorities
) {

    const tbody =
        document.getElementById(
            "authority-table-body"
        );


    if (!tbody) {

        return;

    }


    tbody.innerHTML = "";


    if (!authorities.length) {

        tbody.innerHTML = `
            <tr>
                <td colspan="9">
                    No authorities found.
                </td>
            </tr>
        `;

        return;

    }


    authorities.forEach(
        authority => {

            const totalKm =
                Number(
                    authority.total_km || 0
                );


            const completedKm =
                Number(
                    authority.total_completed_km ||
                    0
                );


            const reviewedKm =
                Number(
                    authority.km_reviewed || 0
                );


            const digitizationPercentage =
                Number(
                    authority.completion_percentage ??
                    (
                        totalKm > 0
                            ? completedKm /
                              totalKm *
                              100
                            : 0
                    )
                );


            const reviewPercentage =
                Number(
                    authority.review_percentage ??
                    (
                        totalKm > 0
                            ? reviewedKm /
                              totalKm *
                              100
                            : 0
                    )
                );


            const schedule =
                Number(
                    authority.days_ahead_behind_schedule ||
                    0
                );


            let scheduleClass =
                "status-on-track";

            let scheduleText =
                "On Track";


            if (schedule > 0) {

                scheduleClass =
                    "status-ahead";

                scheduleText =
                    `${schedule.toFixed(2)} ahead`;

            }
            else if (schedule < 0) {

                scheduleClass =
                    "status-behind";

                scheduleText =
                    `${Math.abs(
                        schedule
                    ).toFixed(2)} behind`;

            }


            const row =
                document.createElement(
                    "tr"
                );


            row.innerHTML = `

                <td>
                    ${escapeHtml(
                        authority.name || ""
                    )}
                </td>

                <td>
                    ${authority.no_grids || 0}
                </td>

                <td>
                    ${totalKm.toFixed(2)}
                </td>

                <td>
                    ${completedKm.toFixed(2)}
                </td>

                <td>
                    ${digitizationPercentage.toFixed(1)}%
                </td>

                <td>
                    ${reviewedKm.toFixed(2)}
                </td>

                <td>
                    ${reviewPercentage.toFixed(1)}%
                </td>

                <td>
                    ${Number(
                        authority.estimated_time_to_complete ||
                        0
                    ).toFixed(1)}
                    days
                </td>

                <td>
                    <span
                        class="status ${scheduleClass}"
                    >
                        ${scheduleText}
                    </span>
                </td>

            `;


            tbody.appendChild(
                row
            );

        }
    );

}


/* ==========================================================
   GRID TABLE
========================================================== */

function renderGrids(
    grids
) {

    const tbody =
        document.getElementById(
            "grid-table-body"
        );


    if (!tbody) {

        return;

    }


    tbody.innerHTML = "";


    if (!grids.length) {

        tbody.innerHTML = `
            <tr>
                <td colspan="12">
                    No grids found.
                </td>
            </tr>
        `;

        return;

    }


    grids.forEach(
        grid => {

            const km =
                Number(
                    grid.km_to_digitize || 0
                );


            const completedKm =
                Number(
                    grid.km_completed || 0
                );


            const progress =
                km > 0
                    ? completedKm /
                      km *
                      100
                    : 0;


            const estimatedDayToWord =
                grid.estimated_completion_day ??
                "-";


            const row =
                document.createElement(
                    "tr"
                );


            row.dataset.gridId =
                grid.id;


            row.innerHTML = `

                <td>
                    ${escapeHtml(
                        grid.grid_id || ""
                    )}
                </td>

                <td>
                    ${escapeHtml(
                        grid.authority_name || ""
                    )}
                </td>

                <td>
                    ${escapeHtml(
                        grid.area_name || ""
                    )}
                </td>

                <td>
                    ${km.toFixed(2)}
                </td>

                <td class="editable-cell completed-km-cell">
                    ${completedKm.toFixed(2)}
                </td>

                <td>
                    ${progress.toFixed(1)}%
                </td>

                <td class="editable-cell status-cell">

                    <span
                        class="status status-${escapeHtml(
                            grid.status || "to_do"
                        )}"
                    >
                        ${escapeHtml(
                            grid.status_display ||
                            grid.status ||
                            "To Do"
                        )}
                    </span>

                </td>

                <td class="editable-cell assigned-cell">
                    ${escapeHtml(
                        grid.assigned_to_name ||
                        "Unassigned"
                    )}
                </td>

                <td>
                    ${formatDate(
                        grid.start_date
                    )}
                </td>

                <td>
                    ${formatDate(
                        grid.complete_date
                    )}
                </td>

                <td>
                    ${escapeHtml(
                        estimatedDayToWord
                    )}
                </td>

                <td>

                    <button
                        type="button"
                        class="grid-edit-button"
                        onclick="editGridRow(this)"
                    >
                        Edit
                    </button>

                </td>

            `;


            tbody.appendChild(
                row
            );

        }
    );

}


/* ==========================================================
   EDIT GRID
========================================================== */

function editGridRow(
    button
) {

    const row =
        button.closest("tr");


    if (!row) {

        return;

    }


    const gridId =
        row.dataset.gridId;


    const grid =
        window.managerGrids.find(
            item =>
                String(item.id) ===
                String(gridId)
        );


    if (!grid) {

        console.error(
            "[Grid Edit] Grid not found:",
            gridId
        );

        return;

    }


    row.querySelector(
        ".completed-km-cell"
    ).innerHTML = `

        <input
            type="number"
            step="0.01"
            min="0"
            class="grid-edit-km"
            value="${Number(
                grid.km_completed || 0
            )}"
        >

    `;


    row.querySelector(
        ".status-cell"
    ).innerHTML = `

        <select class="grid-edit-status">

            <option
                value="to_do"
                ${
                    normalizeStatus(
                        grid.status
                    ) === "to_do"
                        ? "selected"
                        : ""
                }
            >
                To Do
            </option>

            <option
                value="blocked"
                ${
                    normalizeStatus(
                        grid.status
                    ) === "blocked"
                        ? "selected"
                        : ""
                }
            >
                Blocked
            </option>

            <option
                value="in_progress"
                ${
                    normalizeStatus(
                        grid.status
                    ) === "in_progress"
                        ? "selected"
                        : ""
                }
            >
                In Progress
            </option>

            <option
                value="done"
                ${
                    normalizeStatus(
                        grid.status
                    ) === "done"
                        ? "selected"
                        : ""
                }
            >
                Done
            </option>

        </select>

    `;


    button.parentElement.innerHTML = `

        <button
            type="button"
            onclick="saveGridRow(this)"
        >
            Save
        </button>

        <button
            type="button"
            onclick="cancelGridEdit(this)"
        >
            Cancel
        </button>

    `;

}


/* ==========================================================
   SAVE GRID
========================================================== */

async function saveGridRow(
    button
) {

    const row =
        button.closest("tr");


    if (!row) {

        return;

    }


    const gridId =
        row.dataset.gridId;


    const kmInput =
        row.querySelector(
            ".grid-edit-km"
        );


    const statusInput =
        row.querySelector(
            ".grid-edit-status"
        );


    if (
        !kmInput ||
        !statusInput
    ) {

        return;

    }


    const kmCompleted =
        Number(
            kmInput.value
        );


    if (
        !Number.isFinite(
            kmCompleted
        ) ||
        kmCompleted < 0
    ) {

        alert(
            "Please enter a valid completed KM."
        );

        return;

    }


    const payload = {

        km_completed:
            kmCompleted,

        status:
            statusInput.value

    };


    try {

        button.disabled =
            true;

        button.textContent =
            "Saving...";


        const response =
            await fetch(
                `${GRID_API_URL}${gridId}/`,
                {

                    method:
                        "PATCH",

                    headers: {

                        "Content-Type":
                            "application/json",

                        "Accept":
                            "application/json",

                        "X-CSRFToken":
                            getCsrfToken()

                    },

                    credentials:
                        "same-origin",

                    body:
                        JSON.stringify(
                            payload
                        )

                }
            );


        if (!response.ok) {

            const errorData =
                await response
                    .json()
                    .catch(
                        () => null
                    );


            throw new Error(
                errorData
                    ? JSON.stringify(
                        errorData
                    )
                    : `HTTP ${response.status}`
            );

        }


        const updatedGrid =
            await response.json();


        const index =
            window.managerGrids.findIndex(
                item =>
                    String(item.id) ===
                    String(gridId)
            );


        if (index !== -1) {

            window.managerGrids[index] =
                updatedGrid;

        }


        /*
         * Reload the currently selected filters
         * from the backend.
         */

        await loadFilteredDashboard();

    }
    catch (error) {

        console.error(
            "[Grid Edit] Save failed:",
            error
        );


        alert(
            `Failed to save grid: ${error.message}`
        );


        button.disabled =
            false;

        button.textContent =
            "Save";

    }

}


/* ==========================================================
   CANCEL GRID EDIT
========================================================== */

function cancelGridEdit() {

    renderGrids(
        window.managerFilteredGrids
    );

}


/* ==========================================================
   REVIEW TABLE
========================================================== */

function renderReviews(
    reviews
) {

    const tbody =
        document.getElementById(
            "review-table-body"
        );


    if (!tbody) {

        return;

    }


    tbody.innerHTML = "";


    if (!reviews.length) {

        tbody.innerHTML = `
            <tr>
                <td colspan="9">
                    No reviews found.
                </td>
            </tr>
        `;

        return;

    }


    reviews.forEach(
        review => {

            const reviewedKm =
                Number(
                    review.total_km_reviewed || 0
                );


            const reviewPercentage =
                Number(
                    review.percentage_of_total_km_reviewed ||
                    0
                );


            const actualBurndown =
                Number(
                    review.actual_burndown_rate || 0
                );


            const idealBurndown =
                Number(
                    review.ideal_burndown_rate || 0
                );


            const difference =
                Number(
                    review.burndown_difference || 0
                );


            let statusClass =
                "status-on-track";


            let statusText =
                "On Track";


            if (difference > 0) {

                statusClass =
                    "status-ahead";

                statusText =
                    "Ahead";

            }
            else if (difference < 0) {

                statusClass =
                    "status-behind";

                statusText =
                    "Behind";

            }


            const row =
                document.createElement(
                    "tr"
                );


            row.dataset.reviewId =
                review.id;


            row.innerHTML = `

                <td>
                    ${escapeHtml(
                        review.authority_name || ""
                    )}
                </td>

                <td class="review-day-cell">
                    ${review.day || 0}
                </td>

                <td class="review-km-cell">
                    ${reviewedKm.toFixed(2)}
                </td>

                <td>
                    ${reviewPercentage.toFixed(1)}%
                </td>

                <td>
                    ${actualBurndown.toFixed(1)}%
                </td>

                <td>
                    ${idealBurndown.toFixed(1)}%
                </td>

                <td>
                    ${difference.toFixed(1)}%
                </td>

                <td>

                    <span
                        class="status ${statusClass}"
                    >
                        ${statusText}
                    </span>

                </td>

                <td>

                    <button
                        type="button"
                        onclick="editReviewRow(this)"
                    >
                        Edit
                    </button>

                </td>

            `;


            tbody.appendChild(
                row
            );

        }
    );

}


/* ==========================================================
   EDIT REVIEW
========================================================== */

function editReviewRow(
    button
) {

    const row =
        button.closest("tr");


    if (!row) {

        return;

    }


    const reviewId =
        row.dataset.reviewId;


    const review =
        window.managerReviews.find(
            item =>
                String(item.id) ===
                String(reviewId)
        );


    if (!review) {

        return;

    }


    row.querySelector(
        ".review-day-cell"
    ).innerHTML = `

        <input
            type="number"
            min="1"
            step="1"
            class="review-edit-day"
            value="${Number(
                review.day || 1
            )}"
        >

    `;


    row.querySelector(
        ".review-km-cell"
    ).innerHTML = `

        <input
            type="number"
            min="0"
            step="0.01"
            class="review-edit-km"
            value="${Number(
                review.total_km_reviewed || 0
            )}"
        >

    `;


    button.parentElement.innerHTML = `

        <button
            type="button"
            onclick="saveReviewRow(this)"
        >
            Save
        </button>

        <button
            type="button"
            onclick="cancelReviewEdit(this)"
        >
            Cancel
        </button>

    `;

}


/* ==========================================================
   SAVE REVIEW
========================================================== */

async function saveReviewRow(
    button
) {

    const row =
        button.closest("tr");


    if (!row) {

        return;

    }


    const reviewId =
        row.dataset.reviewId;


    const dayInput =
        row.querySelector(
            ".review-edit-day"
        );


    const kmInput =
        row.querySelector(
            ".review-edit-km"
        );


    if (
        !dayInput ||
        !kmInput
    ) {

        return;

    }


    const day =
        Number(
            dayInput.value
        );


    const kmReviewed =
        Number(
            kmInput.value
        );


    if (
        !Number.isFinite(day) ||
        day < 1
    ) {

        alert(
            "Please enter a valid review day."
        );

        return;

    }


    if (
        !Number.isFinite(kmReviewed) ||
        kmReviewed < 0
    ) {

        alert(
            "Please enter a valid reviewed KM."
        );

        return;

    }


    const payload = {

        day:
            day,

        total_km_reviewed:
            kmReviewed

    };


    try {

        button.disabled =
            true;

        button.textContent =
            "Saving...";


        const response =
            await fetch(
                `${REVIEW_API_URL}${reviewId}/`,
                {

                    method:
                        "PATCH",

                    headers: {

                        "Content-Type":
                            "application/json",

                        "Accept":
                            "application/json",

                        "X-CSRFToken":
                            getCsrfToken()

                    },

                    credentials:
                        "same-origin",

                    body:
                        JSON.stringify(
                            payload
                        )

                }
            );


        if (!response.ok) {

            const errorData =
                await response
                    .json()
                    .catch(
                        () => null
                    );


            throw new Error(
                errorData
                    ? JSON.stringify(
                        errorData
                    )
                    : `HTTP ${response.status}`
            );

        }


        /*
         * We don't need to reload ALL authorities.
         *
         * Reload only the currently selected
         * authority's reviews/grids.
         */

        await loadFilteredDashboard();

    }
    catch (error) {

        console.error(
            "[Review Edit] Save failed:",
            error
        );


        alert(
            `Failed to save review: ${error.message}`
        );


        button.disabled =
            false;

        button.textContent =
            "Save";

    }

}


/* ==========================================================
   CANCEL REVIEW
========================================================== */

function cancelReviewEdit() {

    renderReviews(
        window.managerReviews
    );

}


/* ==========================================================
   MAP INITIALIZATION
========================================================== */

async function loadGridMap() {

    const loader =
        document.getElementById(
            "map-loader"
        );


    if (loader) {

        loader.setAttribute(
            "active",
            ""
        );

    }


    try {

        if (
            typeof require !==
            "function"
        ) {

            throw new Error(
                "ArcGIS AMD loader is not available."
            );

        }


        /*
         * IMPORTANT:
         *
         * This is the already-filtered dataset.
         */

        const grids =
            window.managerFilteredMapGrids;


        await new Promise(
            (
                resolve,
                reject
            ) => {

                require(
                    [
                        "esri/Map",
                        "esri/views/MapView",
                        "esri/layers/GraphicsLayer",
                        "esri/Graphic"
                    ],

                    function(
                        Map,
                        MapView,
                        GraphicsLayer,
                        Graphic
                    ) {

                        try {

                            window.managerGraphicClass =
                                Graphic;


                            createGridMap(
                                Map,
                                MapView,
                                GraphicsLayer,
                                Graphic,
                                grids
                            );


                            resolve();

                        }
                        catch (error) {

                            reject(
                                error
                            );

                        }

                    },

                    function(error) {

                        reject(
                            error
                        );

                    }
                );

            }
        );

    }
    catch (error) {

        console.error(
            "[Map] Failed to load:",
            error
        );


        showMapError(
            error
        );

    }
    finally {

        if (loader) {

            loader.removeAttribute(
                "active"
            );

        }

    }

}


/* ==========================================================
   CREATE MAP
========================================================== */

function createGridMap(
    Map,
    MapView,
    GraphicsLayer,
    Graphic,
    grids
) {

    const mapContainer =
        document.getElementById(
            "project-map"
        );


    if (!mapContainer) {

        throw new Error(
            "project-map element not found."
        );

    }


    /*
     * Destroy previous map.
     */

    if (
        window.managerMapView
    ) {

        try {

            window.managerMapView.destroy();

        }
        catch (error) {

            console.warn(
                "[Map] Could not destroy old view:",
                error
            );

        }

    }


    mapContainer.innerHTML =
        "";


    const map =
        new Map({
            basemap:
                "gray-vector"
        });


    const graphicsLayer =
        new GraphicsLayer({

            title:
                "Grid Map"

        });


    map.add(
        graphicsLayer
    );


    const view =
        new MapView({

            container:
                mapContainer,

            map:
                map,

            center: [
                -2.28,
                54.42
            ],

            zoom:
                10

        });


    window.managerMap =
        map;

    window.managerMapView =
        view;

    window.managerGraphicsLayer =
        graphicsLayer;


    updateMapGraphics(
        Graphic,
        grids,
        true
    );


    console.log(
        `[Map] Initialized with ${grids.length} records`
    );


    view.when(
        () => {

            zoomToGraphics();

        },
        error => {

            console.error(
                "[Map] MapView failed:",
                error
            );

            showMapError(
                error
            );

        }
    );

}


/* ==========================================================
   RENDER MAP
========================================================== */

function renderMap(
    grids
) {

    if (
        !window.managerGraphicsLayer
    ) {

        console.log(
            "[Map] Not initialized yet."
        );

        return;

    }


    if (
        !window.managerGraphicClass
    ) {

        console.warn(
            "[Map] Graphic class unavailable."
        );

        return;

    }


    updateMapGraphics(
        window.managerGraphicClass,
        grids,
        false
    );

}


/* ==========================================================
   UPDATE MAP GRAPHICS
========================================================== */

function updateMapGraphics(
    Graphic,
    grids,
    shouldZoom
) {

    const graphicsLayer =
        window.managerGraphicsLayer;


    const view =
        window.managerMapView;


    if (!graphicsLayer) {

        return;

    }


    graphicsLayer.removeAll();


    let validGraphics =
        0;


    let missingGeometry =
        0;


    grids.forEach(
        grid => {

            try {

                const rawGeometry =
                    grid.geom ??
                    grid.geom_json ??
                    grid.geometry;


                if (!rawGeometry) {

                    missingGeometry++;

                    console.warn(
                        "[Map] Grid has no geometry:",
                        {
                            id:
                                grid.id,

                            grid_id:
                                grid.grid_id
                        }
                    );

                    return;

                }


                const geometry =
                    convertToArcGISGeometry(
                        rawGeometry
                    );


                if (!geometry) {

                    console.warn(
                        "[Map] Invalid geometry:",
                        {
                            id:
                                grid.id,

                            grid_id:
                                grid.grid_id
                        }
                    );

                    return;

                }


                const symbol =
                    createGridSymbol(
                        grid
                    );


                const graphic =
                    new Graphic({

                        geometry:
                            geometry,

                        attributes:
                            grid,

                        symbol:
                            symbol,

                        popupTemplate:
                            createGridPopup()

                    });


                graphicsLayer.add(
                    graphic
                );


                validGraphics++;

            }
            catch (error) {

                console.error(
                    `[Map] Failed to render grid ${
                        grid.grid_id ||
                        grid.id
                    }:`,
                    error
                );

            }

        }
    );


    console.log(
        "[Map] Render complete:",
        {
            total:
                grids.length,

            rendered:
                validGraphics,

            missingGeometry:
                missingGeometry,

            renderMode:
                window.managerMapRenderMode
        }
    );


    if (
        shouldZoom &&
        view &&
        view.ready &&
        validGraphics
    ) {

        zoomToGraphics();

    }

}


/* ==========================================================
   ZOOM
========================================================== */

function zoomToGraphics() {

    const view =
        window.managerMapView;


    const graphicsLayer =
        window.managerGraphicsLayer;


    if (
        !view ||
        !graphicsLayer ||
        !graphicsLayer.graphics.length
    ) {

        return;

    }


    view.goTo(
        graphicsLayer.graphics.toArray(),
        {

            padding:
                50,

            duration:
                600

        }
    )
    .catch(
        error => {

            console.warn(
                "[Map] Could not zoom:",
                error
            );

        }
    );

}


/* ==========================================================
   GEOMETRY CONVERSION
========================================================== */

function convertToArcGISGeometry(
    geometry
) {

    if (!geometry) {

        return null;

    }


    /*
     * JSON string.
     */

    if (
        typeof geometry ===
        "string"
    ) {

        const trimmed =
            geometry.trim();


        if (!trimmed) {

            return null;

        }


        try {

            geometry =
                JSON.parse(
                    trimmed
                );

        }
        catch (error) {

            console.error(
                "[Geometry] JSON parse failed:",
                error.message
            );

            return null;

        }

    }


    if (!geometry) {

        return null;

    }


    /*
     * GeoJSON Feature.
     */

    if (
        geometry.type ===
        "Feature"
    ) {

        return convertToArcGISGeometry(
            geometry.geometry
        );

    }


    /*
     * FeatureCollection.
     */

    if (
        geometry.type ===
        "FeatureCollection"
    ) {

        return null;

    }


    /*
     * GeoJSON.
     */

    switch (
        geometry.type
    ) {

        case "Point":

            return convertGeoJSONPoint(
                geometry.coordinates
            );


        case "MultiPoint":

            return convertGeoJSONMultiPoint(
                geometry.coordinates
            );


        case "LineString":

            return convertGeoJSONLineString(
                geometry.coordinates
            );


        case "MultiLineString":

            return convertGeoJSONMultiLineString(
                geometry.coordinates
            );


        case "Polygon":

            return convertGeoJSONPolygon(
                geometry.coordinates
            );


        case "MultiPolygon":

            return convertGeoJSONMultiPolygon(
                geometry.coordinates
            );

    }


    /*
     * Already ArcGIS polygon.
     */

    if (
        Array.isArray(
            geometry.rings
        )
    ) {

        return {

            type:
                "polygon",

            rings:
                geometry.rings,

            spatialReference:
                geometry.spatialReference || {
                    wkid:
                        4326
                }

        };

    }


    /*
     * Already ArcGIS polyline.
     */

    if (
        Array.isArray(
            geometry.paths
        )
    ) {

        return {

            type:
                "polyline",

            paths:
                geometry.paths,

            spatialReference:
                geometry.spatialReference || {
                    wkid:
                        4326
                }

        };

    }


    /*
     * Already ArcGIS multipoint.
     */

    if (
        Array.isArray(
            geometry.points
        )
    ) {

        return {

            type:
                "multipoint",

            points:
                geometry.points,

            spatialReference:
                geometry.spatialReference || {
                    wkid:
                        4326
                }

        };

    }


    /*
     * Already ArcGIS point.
     */

    if (
        geometry.x !== undefined &&
        geometry.y !== undefined
    ) {

        const x =
            Number(
                geometry.x
            );

        const y =
            Number(
                geometry.y
            );


        if (
            !Number.isFinite(x) ||
            !Number.isFinite(y)
        ) {

            return null;

        }


        return {

            type:
                "point",

            x:
                x,

            y:
                y,

            spatialReference:
                geometry.spatialReference || {
                    wkid:
                        4326
                }

        };

    }


    console.warn(
        "[Geometry] Unknown format:",
        geometry
    );


    return null;

}


/* ==========================================================
   GEOJSON POINT
========================================================== */

function convertGeoJSONPoint(
    coordinates
) {

    if (
        !Array.isArray(coordinates) ||
        coordinates.length < 2
    ) {

        return null;

    }


    const x =
        Number(
            coordinates[0]
        );

    const y =
        Number(
            coordinates[1]
        );


    if (
        !Number.isFinite(x) ||
        !Number.isFinite(y)
    ) {

        return null;

    }


    return {

        type:
            "point",

        x:
            x,

        y:
            y,

        spatialReference: {
            wkid:
                4326
        }

    };

}


/* ==========================================================
   GEOJSON MULTIPOINT
========================================================== */

function convertGeoJSONMultiPoint(
    coordinates
) {

    if (
        !Array.isArray(coordinates)
    ) {

        return null;

    }


    return {

        type:
            "multipoint",

        points:
            coordinates,

        spatialReference: {
            wkid:
                4326
        }

    };

}


/* ==========================================================
   GEOJSON LINESTRING
========================================================== */

function convertGeoJSONLineString(
    coordinates
) {

    if (
        !Array.isArray(coordinates)
    ) {

        return null;

    }


    return {

        type:
            "polyline",

        paths: [
            coordinates
        ],

        spatialReference: {
            wkid:
                4326
        }

    };

}


/* ==========================================================
   GEOJSON MULTILINESTRING
========================================================== */

function convertGeoJSONMultiLineString(
    coordinates
) {

    if (
        !Array.isArray(coordinates)
    ) {

        return null;

    }


    return {

        type:
            "polyline",

        paths:
            coordinates,

        spatialReference: {
            wkid:
                4326
        }

    };

}


/* ==========================================================
   GEOJSON POLYGON
========================================================== */

function convertGeoJSONPolygon(
    coordinates
) {

    if (
        !Array.isArray(coordinates) ||
        !coordinates.length
    ) {

        return null;

    }


    return {

        type:
            "polygon",

        rings:
            coordinates,

        spatialReference: {
            wkid:
                4326
        }

    };

}


/* ==========================================================
   GEOJSON MULTIPOLYGON
========================================================== */

function convertGeoJSONMultiPolygon(
    coordinates
) {

    if (
        !Array.isArray(coordinates)
    ) {

        return null;

    }


    const rings = [];


    coordinates.forEach(
        polygon => {

            if (
                !Array.isArray(polygon)
            ) {

                return;

            }


            polygon.forEach(
                ring => {

                    if (
                        Array.isArray(ring)
                    ) {

                        rings.push(
                            ring
                        );

                    }

                }
            );

        }
    );


    if (!rings.length) {

        return null;

    }


    return {

        type:
            "polygon",

        rings:
            rings,

        spatialReference: {
            wkid:
                4326
        }

    };

}


/* ==========================================================
   MAP SYMBOL
========================================================== */

function createGridSymbol(
    grid
) {

    const mode =
        window.managerMapRenderMode ||
        "status";


    if (
        mode === "user"
    ) {

        return createUserSymbol(
            grid
        );

    }


    return createStatusSymbol(
        grid
    );

}


/* ==========================================================
   MAP RENDER MODE CHANGE
========================================================== */

function handleMapRenderModeChanged(
    event
) {

    const value =
        event.target.value ||
        "status";


    window.managerMapRenderMode =
        value;


    console.log(
        "[Map] Render mode changed:",
        value
    );


    renderMap(
        window.managerFilteredMapGrids
    );

}


/* ==========================================================
   STATUS SYMBOL
========================================================== */

function createStatusSymbol(
    grid
) {

    const status =
        normalizeStatus(
            grid.status ||
            grid.status_display ||
            "to_do"
        );


    switch (status) {

        case "done":

        case "completed":

            return {

                type:
                    "simple-fill",

                color: [
                    46,
                    204,
                    113,
                    0.45
                ],

                outline: {

                    color: [
                        39,
                        174,
                        96,
                        1
                    ],

                    width:
                        2

                }

            };


        case "in_progress":

            return {

                type:
                    "simple-fill",

                color: [
                    241,
                    196,
                    15,
                    0.45
                ],

                outline: {

                    color: [
                        243,
                        156,
                        18,
                        1
                    ],

                    width:
                        2

                }

            };


        case "blocked":

            return {

                type:
                    "simple-fill",

                color: [
                    231,
                    76,
                    60,
                    0.45
                ],

                outline: {

                    color: [
                        192,
                        57,
                        43,
                        1
                    ],

                    width:
                        2

                }

            };


        case "to_do":

        default:

            return {

                type:
                    "simple-fill",

                color: [
                    52,
                    152,
                    219,
                    0.45
                ],

                outline: {

                    color: [
                        41,
                        128,
                        185,
                        1
                    ],

                    width:
                        2

                }

            };

    }

}


/* ==========================================================
   USER SYMBOL
========================================================== */

function createUserSymbol(
    grid
) {

    const user =
        grid.assigned_to_id ??
        grid.assigned_to ??
        grid.assigned_to_name ??
        "unassigned";


    const color =
        getUserColor(
            String(user)
        );


    return {

        type:
            "simple-fill",

        color: [

            color[0],
            color[1],
            color[2],
            0.45

        ],

        outline: {

            color: [

                color[0],
                color[1],
                color[2],
                1

            ],

            width:
                2

        }

    };

}


/* ==========================================================
   USER COLOR
========================================================== */

function getUserColor(
    value
) {

    const palette = [

        [31, 119, 180],

        [255, 127, 14],

        [44, 160, 44],

        [214, 39, 40],

        [148, 103, 189],

        [140, 86, 75],

        [227, 119, 194],

        [127, 127, 127],

        [188, 189, 34],

        [23, 190, 207],

        [255, 99, 132],

        [75, 192, 192]

    ];


    let hash =
        0;


    for (
        let i = 0;
        i < value.length;
        i++
    ) {

        hash =
            (
                hash * 31 +
                value.charCodeAt(i)
            ) >>> 0;

    }


    return palette[
        hash %
        palette.length
    ];

}


/* ==========================================================
   MAP POPUP
========================================================== */

function createGridPopup() {

    return {

        title:
            "{grid_id}",

        content: [

            {

                type:
                    "fields",

                fieldInfos: [

                    {

                        fieldName:
                            "authority_name",

                        label:
                            "Authority"

                    },

                    {

                        fieldName:
                            "area_name",

                        label:
                            "Area"

                    },

                    {

                        fieldName:
                            "status_display",

                        label:
                            "Status"

                    },

                    {

                        fieldName:
                            "km_to_digitize",

                        label:
                            "Total KM",

                        format: {

                            places:
                                2,

                            digitSeparator:
                                true

                        }

                    },

                    {

                        fieldName:
                            "km_completed",

                        label:
                            "Completed KM",

                        format: {

                            places:
                                2,

                            digitSeparator:
                                true

                        }

                    },

                    {

                        fieldName:
                            "assigned_to_name",

                        label:
                            "Assigned To"

                    }

                ]

            }

        ]

    };

}


/* ==========================================================
   MAP ERROR
========================================================== */

function showMapError(
    error
) {

    const mapContainer =
        document.getElementById(
            "project-map"
        );


    if (!mapContainer) {

        return;

    }


    if (
        mapContainer.querySelector(
            ".esri-view"
        )
    ) {

        return;

    }


    const message =
        error &&
        error.message
            ? error.message
            : "Unable to load the map.";


    mapContainer.innerHTML = `

        <div
            style="
                display:flex;
                align-items:center;
                justify-content:center;
                height:100%;
                padding:20px;
                text-align:center;
                color:#6b7280;
            "
        >

            <div>

                <strong>
                    Unable to load map
                </strong>

                <div
                    style="
                        margin-top:8px;
                        font-size:0.9rem;
                    "
                >
                    ${escapeHtml(
                        message
                    )}
                </div>

            </div>

        </div>

    `;

}


/* ==========================================================
   DATE
========================================================== */

function formatDate(
    value
) {

    if (!value) {

        return "-";

    }


    const date =
        new Date(value);


    if (
        Number.isNaN(
            date.getTime()
        )
    ) {

        return "-";

    }


    return date.toLocaleDateString();

}


/* ==========================================================
   HTML ESCAPE
========================================================== */

function escapeHtml(
    value
) {

    const div =
        document.createElement(
            "div"
        );


    div.textContent =
        value ?? "";


    return div.innerHTML;

}


/* ==========================================================
   INITIALIZE
========================================================== */

document.addEventListener(
    "DOMContentLoaded",
    () => {

        loadDashboard();

    }
);
