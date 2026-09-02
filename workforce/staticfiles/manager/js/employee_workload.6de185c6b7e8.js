const API_URL =
    "/api/v1/manager/employees/";


async function loadEmployees() {

    const response =
        await fetch(
            API_URL
        );


    if (!response.ok) {

        throw new Error(
            `HTTP ${response.status}`
        );

    }


    const data =
        await response.json();


    const employees =
        Array.isArray(data)
            ? data
            : data.results || [];


    renderSummary(
        employees
    );


    renderEmployees(
        employees
    );

}


/* ==========================================================
   SUMMARY
========================================================== */

function renderSummary(
    employees
) {

    document.getElementById(
        "total-employees"
    ).textContent =
        employees.length;


    const totalGrids =
        employees.reduce(
            (
                sum,
                employee
            ) =>
                sum +
                Number(
                    employee.assigned_grids || 0
                ),
            0
        );


    const totalHours =
        employees.reduce(
            (
                sum,
                employee
            ) =>
                sum +
                Number(
                    employee.estimated_hours || 0
                ),
            0
        );


    const totalKm =
        employees.reduce(
            (
                sum,
                employee
            ) =>
                sum +
                Number(
                    employee.completed_km || 0
                ),
            0
        );


    document.getElementById(
        "total-assigned-grids"
    ).textContent =
        totalGrids;


    document.getElementById(
        "total-estimated-hours"
    ).textContent =
        totalHours.toFixed(1);


    document.getElementById(
        "total-employee-km"
    ).textContent =
        totalKm.toFixed(2);

}


/* ==========================================================
   EMPLOYEE TABLE
========================================================== */

function renderEmployees(
    employees
) {

    const tbody =
        document.getElementById(
            "employee-table-body"
        );


    tbody.innerHTML = "";


    if (!employees.length) {

        tbody.innerHTML = `

            <tr>

                <td colspan="8">

                    No employees found.

                </td>

            </tr>

        `;

        return;

    }


    employees.forEach(
        employee => {

            const assignedGrids =
                Number(
                    employee.assigned_grids || 0
                );


            const completedGrids =
                Number(
                    employee.completed_grids || 0
                );


            const estimatedHours =
                Number(
                    employee.estimated_hours || 0
                );


            const completedKm =
                Number(
                    employee.completed_km || 0
                );


            const totalKm =
                Number(
                    employee.total_km || 0
                );


            const progress =
                totalKm > 0
                    ? (
                        completedKm /
                        totalKm *
                        100
                    )
                    : 0;


            const workingDays =
                Math.ceil(
                    estimatedHours /
                    7.5
                );


            let status =
                "Available";


            if (
                assignedGrids > 0
            ) {

                status =
                    "Working";

            }


            if (
                completedGrids ===
                assignedGrids &&
                assignedGrids > 0
            ) {

                status =
                    "Completed";

            }


            const row =
                document.createElement(
                    "tr"
                );


            row.innerHTML = `

                <td>

                    ${escapeHtml(
                        employee.username ||
                        employee.name ||
                        ""
                    )}

                </td>


                <td>

                    ${assignedGrids}

                </td>


                <td>

                    ${estimatedHours.toFixed(1)} h

                </td>


                <td>

                    ${workingDays}

                </td>


                <td>

                    ${completedGrids}

                </td>


                <td>

                    ${completedKm.toFixed(2)} km

                </td>


                <td>

                    <div
                        class="progress-container"
                    >

                        <calcite-progress
                            value="${Math.min(
                                progress,
                                100
                            )}"
                        ></calcite-progress>

                        <span
                            class="progress-value"
                        >

                            ${progress.toFixed(1)}%

                        </span>

                    </div>

                </td>


                <td>

                    ${status}

                </td>

            `;


            tbody.appendChild(
                row
            );

        }
    );

}


/* ==========================================================
   ESCAPE HTML
========================================================== */

function escapeHtml(
    value
) {

    const div =
        document.createElement(
            "div"
        );


    div.textContent =
        value;


    return div.innerHTML;

}


/* ==========================================================
   INITIALIZE
========================================================== */

document.addEventListener(
    "DOMContentLoaded",
    () => {

        loadEmployees()
            .catch(
                error => {

                    console.error(
                        "Failed to load employees:",
                        error
                    );

                }
            );

    }
);