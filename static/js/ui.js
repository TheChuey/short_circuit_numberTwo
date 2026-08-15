// ui.js

// ======================================================
// MOBILE PANEL CONTROLLER
// ======================================================

export function initializeMobilePanels() {

    // =========================================
    // GET HTML ELEMENTS
    // =========================================

    const menuBtn =
        document.getElementById("menu-btn");

    const panelBtn =
        document.getElementById("panel-btn");

    const sidebar =
        document.getElementById("sidebar");

    const controlPanel =
        document.getElementById("control-panel");

    // =========================================
    // SAFETY CHECKS
    // =========================================

    if (
        !menuBtn ||
        !panelBtn ||
        !sidebar ||
        !controlPanel
    ) {

        console.warn(
            "[UI] Mobile Panel Elements Missing"
        );

        return;
    }

// =========================================
// LEFT SIDEBAR TOGGLE
// =========================================

menuBtn.addEventListener(
    "click",
    (event) => {

        // Prevent bubbling
        event.stopPropagation();

        console.log(
            "[UI] Toggle Sidebar"
        );

        // =====================================
        // CHECK CURRENT STATE
        // =====================================

        const sidebarIsOpen =
            sidebar.classList.contains(
                "active"
            );

        // =====================================
        // CLOSE EVERYTHING FIRST
        // =====================================

        sidebar.classList.remove(
            "active"
        );

        controlPanel.classList.remove(
            "active"
        );

        // =====================================
        // REOPEN ONLY IF IT WAS CLOSED
        // =====================================

        if (!sidebarIsOpen) {

            sidebar.classList.add(
                "active"
            );
        }

        console.log(
            `[UI] Sidebar Open: ${!sidebarIsOpen}`
        );
    }
);


// =========================================
// RIGHT PANEL TOGGLE
// =========================================

panelBtn.addEventListener(
    "click",
    (event) => {

        // Prevent bubbling
        event.stopPropagation();

        console.log(
            "[UI] Toggle Control Panel"
        );

        // =====================================
        // CHECK CURRENT STATE
        // =====================================

        const panelIsOpen =
            controlPanel.classList.contains(
                "active"
            );

        // =====================================
        // CLOSE EVERYTHING FIRST
        // =====================================

        sidebar.classList.remove(
            "active"
        );

        controlPanel.classList.remove(
            "active"
        );

        // =====================================
        // REOPEN ONLY IF IT WAS CLOSED
        // =====================================

        if (!panelIsOpen) {

            controlPanel.classList.add(
                "active"
            );
        }

        console.log(
            `[UI] Control Panel Open: ${!panelIsOpen}`
        );
    }
);

    // =========================================
    // AUTO CLOSE PANELS WHEN RESIZING
    // =========================================

    window.addEventListener(
        "resize",
        () => {

            // Desktop mode
            if (window.innerWidth > 768) {

                sidebar.classList.remove(
                    "active"
                );

                controlPanel.classList.remove(
                    "active"
                );
            }
        }
    );

    // =========================================
    // CLICK OUTSIDE TO CLOSE
    // =========================================

    document.addEventListener(
        "click",
        (event) => {

            const clickedInsideSidebar =
                sidebar.contains(event.target);

            const clickedInsidePanel =
                controlPanel.contains(event.target);

            const clickedMenuButton =
                menuBtn.contains(event.target);

            const clickedPanelButton =
                panelBtn.contains(event.target);

            // Ignore desktop mode
            if (window.innerWidth > 768) {
                return;
            }

            // Close sidebar
            if (
                !clickedInsideSidebar &&
                !clickedMenuButton
            ) {

                sidebar.classList.remove(
                    "active"
                );
            }

            // Close control panel
            if (
                !clickedInsidePanel &&
                !clickedPanelButton
            ) {

                controlPanel.classList.remove(
                    "active"
                );
            }
        }
    );

    console.log(
        "[UI] Mobile Panels Initialized"
    );
}



// ======================================================
// RENDER MODEL DROPDOWN
// ======================================================

export function renderModelDropdown(
    models,
    selectId
) {

    const select =
        document.getElementById(selectId);

    if (!select) {

        console.error(
            `[UI] Select Not Found: ${selectId}`
        );

        return;
    }

    // =========================================
    // CLEAR OLD OPTIONS
    // =========================================

    select.innerHTML = "";

    // =========================================
    // CREATE OPTIONS
    // =========================================

    models.forEach(model => {

        const option =
            document.createElement("option");

        option.value = model.id;

        option.textContent = model.name;

        select.appendChild(option);
    });

    console.log(
        "[UI] Model Dropdown Rendered"
    );
}



// ======================================================
// RENDER AGENT BUTTONS
// ======================================================

export function renderAgentButtons(
    agents,
    containerId
) {

    const container =
        document.getElementById(containerId);

    if (!container) {

        console.error(
            `[UI] Container Missing: ${containerId}`
        );

        return;
    }

    // =========================================
    // REMOVE OLD BUTTONS
    // =========================================

    container.innerHTML = "";

    // =========================================
    // CREATE BUTTONS
    // =========================================

    agents.forEach(agent => {

        const button =
            document.createElement("button");

        button.className = "agent-btn";

        button.id = agent.id;

        button.textContent = agent.name;

        // =====================================
        // DISABLED AGENTS
        // =====================================

        if (!agent.enabled) {

            button.disabled = true;

            button.style.opacity = "0.5";
        }

        // =====================================
        // BUTTON CLICK EVENT
        // =====================================

        button.addEventListener(
            "click",
            () => {

                console.log("=================================");

                console.log(
                    `[HTML] BUTTON CLICKED`
                );

                console.log(
                    `[AGENT NAME] ${agent.name}`
                );

                console.log(
                    `[AGENT ID] ${agent.id}`
                );

                console.log(
                    `[ENDPOINT] ${agent.endpoint}`
                );

                console.log("=================================");

                // =====================================
                // AUTO CLOSE MOBILE PANEL
                // =====================================

                if (window.innerWidth <= 768) {

                    const controlPanel =
                        document.getElementById(
                            "control-panel"
                        );

                    if (controlPanel) {

                        controlPanel.classList.remove(
                            "active"
                        );
                    }
                }
            }
        );

        // =====================================
        // ADD BUTTON TO HTML
        // =====================================

        container.appendChild(button);
    });

    console.log(
        "[UI] Agent Buttons Rendered"
    );
}