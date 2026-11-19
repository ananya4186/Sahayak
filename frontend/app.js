// With Live Server (port 5500) the API is on port 8000.
// When the backend serves the page itself (local port 8000 or the deployed
// site), the API is on the same address, so no base URL is needed.
const API_BASE_URL =
    window.location.port === "5500" ? "http://127.0.0.1:8000" : "";

const form = document.querySelector("#profile-form");
const result = document.querySelector("#result");
const schemeList = document.querySelector("#scheme-list");
const recommendations = document.querySelector("#recommendations");
const goalSelect = form.elements.goal;

const numericFields = new Set([
    "age",
    "annual_family_income",
    "monthly_income",
    "class12_percentile",
]);

const booleanFields = new Set([
    "is_student",
    "regular_degree_course",
    "institution_recognized",
    "receives_other_scholarship",
    "aadhaar_linked_bank_account",
    "course_role_requirements_met",
    "is_unorganised_worker",
    "epfo_covered",
    "esic_covered",
    "nps_covered",
    "income_tax_payer",
]);

function showResult(message, type = "") {
    result.className = `result ${type}`.trim();
    result.textContent = message;
}

function updateGoalFields() {
    const selectedGoal = goalSelect.value;

    document.querySelectorAll("[data-goal-fields]").forEach((section) => {
        const isActive = section.dataset.goalFields === selectedGoal;
        section.hidden = !isActive;
        section.querySelectorAll("input, select").forEach((field) => {
            field.disabled = !isActive;
        });
    });
}

function appendSourceInfo(container, scheme) {
    if (scheme.official_source_url) {
        const link = document.createElement("a");
        link.href = scheme.official_source_url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = "Official source";
        container.appendChild(link);
    }

    const date = document.createElement("small");
    date.textContent = scheme.last_verified
        ? `Source checked: ${scheme.last_verified}`
        : "Source check date not recorded";
    container.appendChild(date);
}

function makeSchemeRow(scheme) {
    const item = document.createElement("li");

    const title = document.createElement("strong");
    title.textContent = scheme.name;
    item.appendChild(title);

    const sourceRow = document.createElement("div");
    sourceRow.className = "source-row";
    appendSourceInfo(sourceRow, scheme);
    item.appendChild(sourceRow);

    return item;
}

async function loadSchemes() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/schemes`);
        if (!response.ok) throw new Error("Could not load schemes.");

        const schemes = await response.json();
        const groups = new Map();

        for (const scheme of schemes) {
            if (!groups.has(scheme.category)) groups.set(scheme.category, []);
            groups.get(scheme.category).push(scheme);
        }

        schemeList.replaceChildren();

        for (const [category, categorySchemes] of groups) {
            const section = document.createElement("section");
            section.className = "scheme-category";

            const heading = document.createElement("h3");
            heading.textContent = category;
            section.appendChild(heading);

            const list = document.createElement("ul");
            list.className = "scheme-list";

            for (const scheme of categorySchemes) {
                list.appendChild(makeSchemeRow(scheme));
            }

            section.appendChild(list);
            schemeList.appendChild(section);
        }
    } catch {
        schemeList.textContent =
            "Could not load schemes. Check that the backend server is running.";
    }
}

function addConditionList(card, headingText, values) {
    if (!values || values.length === 0) return;

    const section = document.createElement("section");
    section.className = "condition-section";

    const heading = document.createElement("h4");
    heading.textContent = headingText;
    section.appendChild(heading);

    const list = document.createElement("ul");
    for (const value of values) {
        const item = document.createElement("li");
        item.textContent = value;
        list.appendChild(item);
    }

    section.appendChild(list);
    card.appendChild(section);
}

// A collapsible block (benefits, documents, steps) so a result card stays short.
function addDetailsBlock(card, summaryText, buildContent) {
    const block = document.createElement("details");
    block.className = "details-block";

    const summary = document.createElement("summary");
    summary.textContent = summaryText;
    block.appendChild(summary);

    buildContent(block);
    card.appendChild(block);
}

function makeList(values, ordered = false) {
    const list = document.createElement(ordered ? "ol" : "ul");
    for (const value of values) {
        const item = document.createElement("li");
        item.textContent = value;
        list.appendChild(item);
    }
    return list;
}

function addDocumentGroup(container, headingText, values) {
    if (!values || values.length === 0) return;

    const heading = document.createElement("h5");
    heading.textContent = headingText;
    container.appendChild(heading);
    container.appendChild(makeList(values));
}

function addSchemeDetails(card, item) {
    if (item.benefits && item.benefits.length > 0) {
        addDetailsBlock(card, "What you may get", (block) => {
            block.appendChild(makeList(item.benefits));
        });
    }

    const documents = item.documents || {};
    const hasDocuments =
        (documents.mandatory && documents.mandatory.length > 0) ||
        (documents.conditional && documents.conditional.length > 0);

    if (hasDocuments) {
        addDetailsBlock(card, "Documents to keep ready", (block) => {
            addDocumentGroup(block, "Needed for everyone", documents.mandatory);
            addDocumentGroup(
                block,
                "Needed only in some cases",
                documents.conditional
            );
        });
    }

    if (item.application_steps && item.application_steps.length > 0) {
        addDetailsBlock(card, "How to apply", (block) => {
            block.appendChild(makeList(item.application_steps, true));

            const note = document.createElement("p");
            note.className = "apply-note";
            note.textContent =
                "Sahayak does not submit applications. You apply on the official portal.";
            block.appendChild(note);
        });
    }
}

function addLinks(card, item) {
    const row = document.createElement("div");
    row.className = "source-row";

    if (item.official_apply_url) {
        const apply = document.createElement("a");
        apply.href = item.official_apply_url;
        apply.target = "_blank";
        apply.rel = "noopener noreferrer";
        apply.textContent = "Open the official portal";
        row.appendChild(apply);
    }

    appendSourceInfo(row, item);
    card.appendChild(row);

    if (item.sources && item.sources.length > 0) {
        addDetailsBlock(card, "Sources used for these details", (block) => {
            const list = document.createElement("ul");

            for (const source of item.sources) {
                const entry = document.createElement("li");
                const link = document.createElement("a");
                link.href = source.url;
                link.target = "_blank";
                link.rel = "noopener noreferrer";
                link.textContent = source.title;
                entry.appendChild(link);
                list.appendChild(entry);
            }

            block.appendChild(list);
        });
    }
}

function makeRecommendationCard(item) {
    const card = document.createElement("article");
    card.className = "recommendation-card";

    const heading = document.createElement("div");
    heading.className = "recommendation-heading";

    const title = document.createElement("h3");
    title.textContent = item.name;

    const status = document.createElement("span");
    status.className = `status status-${item.status.toLowerCase().replaceAll(" ", "-")}`;
    status.textContent = item.status;

    heading.append(title, status);
    card.appendChild(heading);

    if (item.description) {
        const description = document.createElement("p");
        description.className = "scheme-description";
        description.textContent = item.description;
        card.appendChild(description);
    }

    if (item.status_notice) {
        const notice = document.createElement("p");
        notice.className = "notice";
        notice.setAttribute("role", "note");
        notice.textContent = item.status_notice;
        card.appendChild(notice);
    }

    const explanation = document.createElement("p");
    explanation.textContent = item.explanation;
    card.appendChild(explanation);

    addConditionList(card, "Matched", item.matched_conditions);
    addConditionList(card, "Failed", item.failed_conditions);
    addConditionList(card, "Information needed", item.missing_information);

    addSchemeDetails(card, item);
    addLinks(card, item);

    return card;
}

function createProfile() {
    const profile = {};
    const formData = new FormData(form);

    for (const [key, rawValue] of formData.entries()) {
        const value = rawValue.trim();
        if (value === "") continue;

        if (numericFields.has(key)) {
            profile[key] = Number(value);
        } else if (booleanFields.has(key)) {
            profile[key] = value === "true";
        } else {
            profile[key] = value;
        }
    }

    return profile;
}

goalSelect.addEventListener("change", updateGoalFields);

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    showResult("Finding schemes for your selected goal…");
    recommendations.replaceChildren();

    try {
        const response = await fetch(`${API_BASE_URL}/api/schemes/recommend`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(createProfile()),
        });

        const data = await response.json();

        if (!response.ok) {
            const message = Array.isArray(data.detail)
                ? data.detail.map((error) => error.msg).join(", ")
                : data.detail || "Please check your entries.";
            showResult(message, "error");
            return;
        }

        showResult(`Showing results for: ${data.goal_label}`, "success");

        if (data.recommendations.length === 0) {
            recommendations.textContent = "No schemes are listed for this category yet.";
            return;
        }

        for (const item of data.recommendations) {
            recommendations.appendChild(makeRecommendationCard(item));
        }
    } catch {
        showResult(
            "Could not connect to the Sahayak API. Make sure the backend is running.",
            "error"
        );
    }
});

updateGoalFields();
loadSchemes();