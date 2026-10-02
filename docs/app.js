/**
 * Personal Expense Tracker — Dashboard Application Logic
 * Integrates with window.EXPENSE_DATA (Aggregated Public Publication Model)
 * Strictly zero transaction rows, zero individual purchase notes, zero IDs.
 */

(function () {
  "use strict";

  // 1. Data Initialization & Validation
  const DATA = window.EXPENSE_DATA;
  if (!DATA) {
    console.error("EXPENSE_DATA payload is missing. Ensure docs/data.js is loaded prior to app.js.");
    const container = document.getElementById("kpiStrip");
    if (container) {
      container.innerHTML = '<div style="padding:20px;color:#A5402F;">Error: Public data payload (docs/data.js) could not be loaded.</div>';
    }
    return;
  }

  const { meta, kpis_overall, monthly_series, category_summary, payment_mode_summary, day_type_summary, filters: dataFilters } = DATA;

  // 2. Color Palette & Formatting Utilities (Power BI Design Tokens)
  const INK = "#0f172a", MUTE = "#475569", RULE = "#e2e8f0", CARD = "#ffffff", GOLD = "#d97706";
  const INCOME = "#059669", EXPENSE = "#dc2626", INVEST = "#2563eb";
  const TYPE_COLOR = { Income: INCOME, Expense: EXPENSE, "Transfer-Out": INVEST };

  function fmtINR(n) {
    const sign = n < 0 ? "-" : "";
    n = Math.abs(n);
    if (n >= 10000000) return sign + "₹" + (n / 10000000).toFixed(2) + "Cr";
    if (n >= 100000) return sign + "₹" + (n / 100000).toFixed(2) + "L";
    if (n >= 1000) return sign + "₹" + Math.round(n / 1000) + "K";
    return sign + "₹" + Math.round(n);
  }

  function fmtINRFull(n) {
    return "₹" + Math.round(n).toLocaleString("en-IN");
  }

  // 3. Application State
  const activeFilters = { year: "", month: "", type: "", cat: "", mode: "", wknd: "" };
  let viewMode = "total"; // "total" | "avg"
  let drillCat = null;
  const charts = {};
  let explorerCurrentPage = 1;
  const EXPLORER_PAGE_SIZE = 5;

  // 4. Setup Toolbar Select Options
  const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  function fillSelect(id, options, allLabel) {
    const sel = document.getElementById(id);
    if (!sel) return;
    sel.innerHTML = "";
    const optAll = document.createElement("option");
    optAll.value = "";
    optAll.textContent = allLabel;
    sel.appendChild(optAll);
    options.forEach((o) => {
      const opt = document.createElement("option");
      opt.value = o.value !== undefined ? o.value : o;
      opt.textContent = o.label !== undefined ? o.label : o;
      sel.appendChild(opt);
    });
  }

  fillSelect("selYear", dataFilters.available_years, "All years");
  fillSelect("selMonth", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map((m, i) => ({ value: m, label: monthNames[i] })), "All months");
  fillSelect("selType", dataFilters.available_transaction_types, "All types");
  fillSelect("selCat", dataFilters.available_categories, "All categories");
  fillSelect("selMode", dataFilters.available_payment_modes, "All modes");

  // 5. Event Listeners
  ["selYear", "selMonth", "selType", "selCat", "selMode"].forEach((id) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.addEventListener("change", (e) => {
      const key = { selYear: "year", selMonth: "month", selType: "type", selCat: "cat", selMode: "mode" }[id];
      activeFilters[key] = e.target.value;
      explorerCurrentPage = 1; // Reset to page 1 on filter change
      renderAll();
    });
  });

  const selWknd = document.getElementById("selWknd");
  if (selWknd) {
    selWknd.addEventListener("change", (e) => {
      activeFilters.wknd = e.target.value;
      explorerCurrentPage = 1; // Reset to page 1 on filter change
      renderAll();
    });
  }

  const viewToggleButtons = document.querySelectorAll("#viewToggle button");
  viewToggleButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      viewMode = btn.dataset.mode;
      viewToggleButtons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      renderKPIs(getFilteredMonths(), getFilteredCategories());
    });
  });

  const resetBtn = document.getElementById("resetBtn");
  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      activeFilters.year = "";
      activeFilters.month = "";
      activeFilters.type = "";
      activeFilters.cat = "";
      activeFilters.mode = "";
      activeFilters.wknd = "";
      ["selYear", "selMonth", "selType", "selCat", "selMode", "selWknd"].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.value = "";
      });
      viewMode = "total";
      viewToggleButtons.forEach((b) => {
        if (b.dataset.mode === "total") {
          b.classList.add("active");
        } else {
          b.classList.remove("active");
        }
      });
      drillCat = null;
      explorerCurrentPage = 1; // Reset to page 1 on filter reset
      renderAll();
    });
  }

  const drillClose = document.getElementById("drillClose");
  if (drillClose) {
    drillClose.addEventListener("click", () => {
      drillCat = null;
      const panel = document.getElementById("drillPanel");
      if (panel) panel.classList.remove("show");
      makeTopCat(getFilteredCategories());
    });
  }

  // Slicer Synchronization Helper for Chart Click Interactions
  function setToolbarFilter(key, val) {
    if (activeFilters[key] === String(val)) {
      activeFilters[key] = "";
    } else {
      activeFilters[key] = String(val);
    }
    const idMap = {
      year: "selYear",
      month: "selMonth",
      type: "selType",
      cat: "selCat",
      mode: "selMode",
      wknd: "selWknd"
    };
    const el = document.getElementById(idMap[key]);
    if (el) el.value = activeFilters[key];
    explorerCurrentPage = 1;
    renderAll();
  }

  // 6. Chart.js Global Configuration (Power BI Design System)
  if (window.Chart) {
    Chart.defaults.font.family = "'Segoe UI', -apple-system, BlinkMacSystemFont, 'Inter', Roboto, sans-serif";
    Chart.defaults.font.size = 12;
    Chart.defaults.color = "#334155";
  }

  const tooltipBase = {
    backgroundColor: "rgba(15, 23, 42, 0.95)",
    titleColor: "#ffffff",
    titleFont: { family: "'Segoe UI', sans-serif", size: 13, weight: "600" },
    bodyColor: "#f8fafc",
    bodyFont: { family: "'Segoe UI', sans-serif", size: 12 },
    footerColor: "#94a3b8",
    footerFont: { family: "'Segoe UI', sans-serif", size: 11, style: "italic" },
    borderColor: "#334155",
    borderWidth: 1,
    padding: { top: 8, bottom: 8, left: 12, right: 12 },
    cornerRadius: 6,
    boxPadding: 4,
    displayColors: true,
  };

  function destroyChart(id) {
    if (charts[id]) {
      charts[id].destroy();
      delete charts[id];
    }
  }

  // 7. Slicing & Filter Helpers
  function getFilteredMonths() {
    return monthly_series.filter((m) =>
      (!activeFilters.year || m.year === +activeFilters.year) &&
      (!activeFilters.month || m.month === +activeFilters.month)
    );
  }

  function getFilteredCategories() {
    if (!activeFilters.cat) return category_summary;
    return category_summary.filter((c) => c.category === activeFilters.cat);
  }

  function getFilteredPaymentModes() {
    if (!activeFilters.mode) return payment_mode_summary;
    return payment_mode_summary.filter((p) => p.payment_mode === activeFilters.mode);
  }

  // 8. Render KPIs
  function renderKPIs(filteredMonths, filteredCats) {
    const isFilteredByTime = !!(activeFilters.year || activeFilters.month);
    let income = 0;
    let expense = 0;
    let invest = 0;

    if (isFilteredByTime) {
      income = filteredMonths.reduce((s, m) => s + m.income, 0);
      expense = filteredMonths.reduce((s, m) => s + m.expense, 0);
      invest = filteredMonths.reduce((s, m) => s + m.transfers, 0);
    } else {
      income = kpis_overall.total_income;
      expense = kpis_overall.total_expense;
      invest = kpis_overall.total_transfers;
    }

    // Type filter adjustment
    if (activeFilters.type === "Income") {
      expense = 0;
      invest = 0;
    } else if (activeFilters.type === "Expense") {
      income = 0;
      invest = 0;
    } else if (activeFilters.type === "Transfer-Out") {
      income = 0;
      expense = 0;
    }

    // Category filter adjustment
    if (activeFilters.cat) {
      const match = category_summary.find((c) => c.category === activeFilters.cat);
      if (match) {
        expense = match.total_spend;
      }
    }

    // Payment mode filter adjustment
    if (activeFilters.mode) {
      const match = payment_mode_summary.find((p) => p.payment_mode === activeFilters.mode);
      if (match) {
        expense = match.total_amount;
      }
    }

    // Weekend filter adjustment
    if (activeFilters.wknd === "we") {
      expense = day_type_summary.weekend.total_spend;
    } else if (activeFilters.wknd === "wk") {
      expense = day_type_summary.weekday.total_spend;
    }

    const nMonths = Math.max(filteredMonths.length, 1);
    const savingsRate = income > 0 ? ((income - expense) / income * 100) : (income === 0 && expense === 0 ? 0 : -100);
    const avgMonthlySpend = expense / nMonths;
    const perMonth = viewMode === "avg";

    const topCatObj = filteredCats.length ? filteredCats[0] : null;

    const kpis = [
      {
        label: "Total Income",
        value: fmtINR(perMonth ? income / nMonths : income),
        sub: perMonth ? "per month" : `${nMonths} month${nMonths > 1 ? "s" : ""}`,
        cls: "income",
      },
      {
        label: "Total Expenses",
        value: fmtINR(perMonth ? expense / nMonths : expense),
        sub: perMonth ? "per month" : `${filteredCats.length} categories`,
        cls: "expense",
      },
      {
        label: "Total Invested",
        value: fmtINR(perMonth ? invest / nMonths : invest),
        sub: perMonth ? "per month" : "transfers-out",
        cls: "invest",
      },
      {
        label: "Net Savings Rate",
        value: income > 0 ? savingsRate.toFixed(1) + "%" : "N/A",
        sub: "(Income − Expense) / Income",
        cls: savingsRate >= 0 ? "income" : "expense",
      },
      {
        label: "Avg Monthly Spend",
        value: fmtINR(avgMonthlySpend),
        sub: `${nMonths} month${nMonths > 1 ? "s" : ""} in range`,
        cls: "",
      },
      {
        label: "Top Category",
        value: topCatObj ? topCatObj.category : "—",
        sub: topCatObj ? fmtINR(topCatObj.total_spend) : "",
        cls: "",
      },
    ];

    const strip = document.getElementById("kpiStrip");
    if (strip) {
      strip.innerHTML = "";
      kpis.forEach((k) => {
        const cell = document.createElement("div");
        cell.className = "kpi-cell";
        cell.innerHTML = `<div class="kpi-label">${k.label}</div><div class="kpi-value${k.cls ? " " + k.cls : ""}">${k.value}</div><div class="kpi-sub">${k.sub}</div>`;
        strip.appendChild(cell);
      });
    }

    const activeCount = Object.values(activeFilters).filter((v) => v).length;
    const periodTag = document.getElementById("periodTag");
    if (periodTag) {
      periodTag.innerHTML = `${nMonths} months (${meta.min_date} – ${meta.max_date})${activeCount ? `<br/>${activeCount} active filter${activeCount > 1 ? "s" : ""}` : "<br/>₹ INR"}`;
    }
  }

  // 9. Render Dynamic Insights
  function renderInsights(filteredMonths, filteredCats) {
    const out = [];
    const topCatObj = filteredCats.length ? filteredCats[0] : null;

    if (topCatObj) {
      out.push(
        `${topCatObj.category} accounts for ${fmtINR(topCatObj.total_spend)} (${topCatObj.percentage_share}%) of total tracked expenses, representing the largest spending category.`
      );
    }

    // Savings rate trajectory comparison
    const y2015 = monthly_series.filter((m) => m.year === 2015);
    const y2018 = monthly_series.filter((m) => m.year === 2018);
    const inc2015 = y2015.reduce((s, m) => s + m.income, 0);
    const exp2015 = y2015.reduce((s, m) => s + m.expense, 0);
    const inc2018 = y2018.reduce((s, m) => s + m.income, 0);
    const exp2018 = y2018.reduce((s, m) => s + m.expense, 0);

    if (inc2015 > 0 && inc2018 > 0) {
      const rate2015 = ((inc2015 - exp2015) / inc2015) * 100;
      const rate2018 = ((inc2018 - exp2018) / inc2018) * 100;
      out.push(
        `Annual savings rate strengthened from ${rate2015.toFixed(1)}% in 2015 to ${rate2018.toFixed(1)}% in 2018, demonstrating positive long-term cash flow discipline.`
      );
    }

    // Weekend vs Weekday analysis
    const weAvg = day_type_summary.weekend.average_daily_spend;
    const wkAvg = day_type_summary.weekday.average_daily_spend;
    out.push(
      `Weekend daily spending averages ${fmtINRFull(weAvg)} versus ${fmtINRFull(wkAvg)} on weekdays — a +${(((weAvg - wkAvg) / wkAvg) * 100).toFixed(1)}% uptick on weekend days.`
    );

    // Investment ratio
    const totalTransfers = kpis_overall.total_transfers;
    const totalExpense = kpis_overall.total_expense;
    if (totalExpense > 0) {
      const invRatio = (totalTransfers / totalExpense) * 100;
      out.push(
        `₹${fmtINR(totalTransfers).replace("₹", "")} has moved into transfers & investments against ${fmtINR(totalExpense)} in expenses — an investment-to-expense ratio of ${invRatio.toFixed(1)}%.`
      );
    }

    // Payment mode insight
    if (payment_mode_summary.length > 0) {
      const topMode = payment_mode_summary[0];
      out.push(
        `${topMode.payment_mode} is the primary payment mode, handling ${fmtINR(topMode.total_amount)} (${topMode.percentage_share}% of total spend) across ${topMode.transaction_count.toLocaleString()} transactions.`
      );
    }

    const grid = document.getElementById("insightsGrid");
    if (!grid) return;
    grid.innerHTML = "";
    out.forEach((text, i) => {
      const div = document.createElement("div");
      div.className = "insight-item";
      div.innerHTML = `<span class="insight-idx">${String(i + 1).padStart(2, "0")}</span><span>${text}</span>`;
      grid.appendChild(div);
    });
  }

  // 10. Chart 1: Monthly Income vs Expense vs Investment
  function makeTrend(filteredMonths) {
    destroyChart("chartTrend");
    const canvas = document.getElementById("chartTrend");
    if (!canvas) return;

    const labels = filteredMonths.map((m) => m.month_year);
    const incData = filteredMonths.map((m) => m.income);
    const expData = filteredMonths.map((m) => m.expense);
    const invData = filteredMonths.map((m) => m.transfers);

    charts.chartTrend = new Chart(canvas, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "Income",
            data: incData,
            borderColor: INCOME,
            backgroundColor: INCOME,
            pointRadius: 0,
            pointHoverRadius: 6,
            pointHoverBackgroundColor: INCOME,
            pointHoverBorderColor: "#ffffff",
            pointHoverBorderWidth: 2,
            borderWidth: 2.2,
            tension: 0.25,
          },
          {
            label: "Expense",
            data: expData,
            borderColor: EXPENSE,
            backgroundColor: EXPENSE,
            pointRadius: 0,
            pointHoverRadius: 6,
            pointHoverBackgroundColor: EXPENSE,
            pointHoverBorderColor: "#ffffff",
            pointHoverBorderWidth: 2,
            borderWidth: 2.2,
            tension: 0.25,
          },
          {
            label: "Investment",
            data: invData,
            borderColor: INVEST,
            backgroundColor: INVEST,
            pointRadius: 0,
            pointHoverRadius: 6,
            pointHoverBackgroundColor: INVEST,
            pointHoverBorderColor: "#ffffff",
            pointHoverBorderWidth: 2,
            borderWidth: 2.2,
            tension: 0.25,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        onClick: (evt, els) => {
          if (els.length) {
            const idx = els[0].index;
            const m = filteredMonths[idx];
            if (m) {
              if (activeFilters.year === String(m.year) && activeFilters.month === String(m.month)) {
                activeFilters.year = "";
                activeFilters.month = "";
              } else {
                activeFilters.year = String(m.year);
                activeFilters.month = String(m.month);
              }
              const yEl = document.getElementById("selYear");
              const mEl = document.getElementById("selMonth");
              if (yEl) yEl.value = activeFilters.year;
              if (mEl) mEl.value = activeFilters.month;
              explorerCurrentPage = 1;
              renderAll();
            }
          }
        },
        onHover: (evt, els) => {
          evt.native.target.style.cursor = els.length ? "pointer" : "default";
        },
        plugins: {
          legend: {
            position: "bottom",
            labels: {
              boxWidth: 12,
              boxHeight: 12,
              usePointStyle: true,
              pointStyle: "circle",
              font: { size: 11.5, weight: "500" },
              color: "#334155",
              padding: 14,
            },
          },
          tooltip: {
            ...tooltipBase,
            mode: "index",
            intersect: false,
            callbacks: {
              title: (items) => {
                if (!items.length) return "";
                const idx = items[0].dataIndex;
                const m = filteredMonths[idx];
                return m ? `${monthNames[m.month - 1]} ${m.year} (${m.month_year})` : items[0].label;
              },
              label: (c) => ` ${c.dataset.label}: ${fmtINRFull(c.parsed.y)}`,
              footer: (items) => {
                if (!items.length) return "";
                const idx = items[0].dataIndex;
                const m = filteredMonths[idx];
                if (!m) return "";
                const net = m.income - m.expense - m.transfers;
                return `Net Cash Flow: ${net >= 0 ? "+" : ""}${fmtINRFull(net)}\n(Click to filter by this month)`;
              },
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { font: { size: 10.5 }, color: "#475569", maxTicksLimit: 12 },
          },
          y: {
            grid: { color: RULE },
            ticks: { font: { size: 11 }, color: "#475569", callback: (v) => fmtINR(v) },
          },
        },
      },
    });
  }

  // 11. Chart 2: Transaction Type Split
  function makeTypeDonut(filteredMonths) {
    destroyChart("chartTypeDonut");
    const canvas = document.getElementById("chartTypeDonut");
    if (!canvas) return;

    let income = 0, expense = 0, invest = 0;
    if (activeFilters.year || activeFilters.month) {
      income = filteredMonths.reduce((s, m) => s + m.income, 0);
      expense = filteredMonths.reduce((s, m) => s + m.expense, 0);
      invest = filteredMonths.reduce((s, m) => s + m.transfers, 0);
    } else {
      income = kpis_overall.total_income;
      expense = kpis_overall.total_expense;
      invest = kpis_overall.total_transfers;
    }

    const sums = { Income: income, Expense: expense, "Transfer-Out": invest };
    const labels = ["Income", "Expense", "Transfer-Out"].filter((t) => sums[t] > 0);
    const total = Object.values(sums).reduce((a, b) => a + b, 0);

    charts.chartTypeDonut = new Chart(canvas, {
      type: "doughnut",
      data: {
        labels,
        datasets: [
          {
            data: labels.map((l) => sums[l]),
            backgroundColor: labels.map((l) => TYPE_COLOR[l]),
            borderWidth: 2,
            borderColor: CARD,
            hoverOffset: 8,
            hoverBorderWidth: 2,
            hoverBorderColor: "#ffffff",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "58%",
        onClick: (evt, els) => {
          if (els.length) {
            const type = labels[els[0].index];
            setToolbarFilter("type", type);
          }
        },
        onHover: (evt, els) => {
          evt.native.target.style.cursor = els.length ? "pointer" : "default";
        },
        plugins: {
          legend: {
            position: "bottom",
            labels: {
              boxWidth: 12,
              boxHeight: 12,
              font: { size: 11.5, weight: "500" },
              color: "#334155",
              padding: 14,
            },
          },
          tooltip: {
            ...tooltipBase,
            callbacks: {
              title: (items) => (items.length ? items[0].label : ""),
              label: (c) => {
                const val = c.parsed;
                const pct = total ? ((val / total) * 100).toFixed(1) + "%" : "0%";
                return ` Total Amount: ${fmtINRFull(val)} (${pct})`;
              },
              footer: (items) =>
                items.length
                  ? `(Click to ${activeFilters.type === items[0].label ? "clear" : "filter by"} ${items[0].label})`
                  : "",
            },
          },
        },
      },
    });

    const noteEl = document.getElementById("typeDonutNote");
    if (noteEl) {
      noteEl.textContent = `Expense makes up ${total ? Math.round((sums.Expense / total) * 100) : 0}% of total ₹ movement`;
    }
  }

  // 12. Chart 3: Top 10 Spending Categories (With Interactive Drilldown)
  function makeTopCat(filteredCats) {
    destroyChart("chartTopCat");
    const canvas = document.getElementById("chartTopCat");
    if (!canvas) return;

    const rows = filteredCats.slice(0, 10);

    charts.chartTopCat = new Chart(canvas, {
      type: "bar",
      data: {
        labels: rows.map((r) => r.category),
        datasets: [
          {
            data: rows.map((r) => r.total_spend),
            backgroundColor: rows.map((r) => (r.category === drillCat ? GOLD : EXPENSE)),
            hoverBackgroundColor: rows.map((r) => (r.category === drillCat ? "#b45309" : "#b91c1c")),
            borderRadius: 4,
          },
        ],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        onClick: (evt, els) => {
          if (els.length) {
            const cat = rows[els[0].index].category;
            drillCat = drillCat === cat ? null : cat;
            renderDrill();
            makeTopCat(filteredCats);
            const drillEl = document.getElementById("drillPanel");
            if (drillEl && typeof drillEl.scrollIntoView === "function" && drillCat) {
              drillEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
            }
          }
        },
        onHover: (evt, els) => {
          evt.native.target.style.cursor = els.length ? "pointer" : "default";
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            ...tooltipBase,
            callbacks: {
              title: (items) => (items.length ? items[0].label : ""),
              label: (c) => {
                const row = rows[c.dataIndex];
                return [
                  ` Total Spend: ${fmtINRFull(c.parsed.x)} (${row ? row.percentage_share : 0}% of expenses)`,
                  ` Transactions: ${row ? row.transaction_count.toLocaleString() : "N/A"}`,
                ];
              },
              footer: () => "(Click bar to toggle subcategory breakdown)",
            },
          },
        },
        scales: {
          x: {
            grid: { color: RULE },
            ticks: { font: { size: 11 }, color: "#475569", callback: (v) => fmtINR(v) },
          },
          y: {
            grid: { display: false },
            ticks: { font: { size: 11, weight: "500" }, color: "#1e293b" },
          },
        },
      },
    });
  }

  // 13. Chart 4: Spend by Payment Mode
  function makePaymentMode(filteredModes) {
    destroyChart("chartPaymentMode");
    const canvas = document.getElementById("chartPaymentMode");
    if (!canvas) return;

    charts.chartPaymentMode = new Chart(canvas, {
      type: "bar",
      data: {
        labels: filteredModes.map((r) => r.payment_mode),
        datasets: [
          {
            data: filteredModes.map((r) => r.total_amount),
            backgroundColor: filteredModes.map((r) => (r.payment_mode === activeFilters.mode ? GOLD : "#0284c7")),
            hoverBackgroundColor: filteredModes.map((r) => (r.payment_mode === activeFilters.mode ? "#b45309" : "#0369a1")),
            borderRadius: 4,
          },
        ],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        onClick: (evt, els) => {
          if (els.length) {
            const mode = filteredModes[els[0].index].payment_mode;
            setToolbarFilter("mode", mode);
          }
        },
        onHover: (evt, els) => {
          evt.native.target.style.cursor = els.length ? "pointer" : "default";
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            ...tooltipBase,
            callbacks: {
              title: (items) => (items.length ? items[0].label : ""),
              label: (c) => {
                const r = filteredModes[c.dataIndex];
                return [
                  ` Total Amount: ${fmtINRFull(c.parsed.x)} (${r ? r.percentage_share : 0}% of spend)`,
                  ` Transactions: ${r ? r.transaction_count.toLocaleString() : "N/A"}`,
                ];
              },
              footer: (items) =>
                items.length
                  ? `(Click to ${activeFilters.mode === items[0].label ? "clear" : "filter by"} ${items[0].label})`
                  : "",
            },
          },
        },
        scales: {
          x: {
            grid: { color: RULE },
            ticks: { font: { size: 11 }, color: "#475569", callback: (v) => fmtINR(v) },
          },
          y: {
            grid: { display: false },
            ticks: { font: { size: 11, weight: "500" }, color: "#1e293b" },
          },
        },
      },
    });
  }

  // 14. Chart 5: Weekday vs Weekend Spending
  function makeWeekend() {
    destroyChart("chartWeekend");
    const canvas = document.getElementById("chartWeekend");
    if (!canvas) return;

    const wkAvg = day_type_summary.weekday.average_daily_spend;
    const weAvg = day_type_summary.weekend.average_daily_spend;

    charts.chartWeekend = new Chart(canvas, {
      type: "bar",
      data: {
        labels: ["Weekday", "Weekend"],
        datasets: [
          {
            data: [Math.round(wkAvg), Math.round(weAvg)],
            backgroundColor: [
              activeFilters.wknd === "wk" ? GOLD : EXPENSE,
              activeFilters.wknd === "we" ? "#b45309" : GOLD,
            ],
            hoverBackgroundColor: ["#b91c1c", "#b45309"],
            borderRadius: 4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        onClick: (evt, els) => {
          if (els.length) {
            const code = els[0].index === 0 ? "wk" : "we";
            setToolbarFilter("wknd", code);
          }
        },
        onHover: (evt, els) => {
          evt.native.target.style.cursor = els.length ? "pointer" : "default";
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            ...tooltipBase,
            callbacks: {
              title: (items) => (items.length ? items[0].label : ""),
              label: (c) => {
                const isWk = c.dataIndex === 0;
                const obj = isWk ? day_type_summary.weekday : day_type_summary.weekend;
                const totalDaySpend = day_type_summary.weekday.total_spend + day_type_summary.weekend.total_spend;
                const pct = totalDaySpend > 0 ? ((obj.total_spend / totalDaySpend) * 100).toFixed(1) + "%" : "0%";
                return [
                  ` Daily Average: ${fmtINRFull(c.parsed.y)} / day`,
                  ` Total Spend: ${fmtINRFull(obj.total_spend)} (${pct})`,
                  ` Tracked Days: ${obj.distinct_calendar_days.toLocaleString()} days`,
                ];
              },
              footer: (items) =>
                items.length
                  ? `(Click to ${activeFilters.wknd ? "clear" : "filter by"} ${items[0].label})`
                  : "",
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { font: { size: 11.5, weight: "600" }, color: "#1e293b" },
          },
          y: {
            grid: { color: RULE },
            ticks: { font: { size: 11 }, color: "#475569", callback: (v) => fmtINR(v) },
          },
        },
      },
    });
  }

  // 15. Chart 6: Monthly Net Savings
  function makeNetSavings(filteredMonths) {
    destroyChart("chartNetSavings");
    const canvas = document.getElementById("chartNetSavings");
    if (!canvas) return;

    const labels = filteredMonths.map((m) => m.month_year);
    const netData = filteredMonths.map((m) => Math.round(m.net_cash_flow));

    charts.chartNetSavings = new Chart(canvas, {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            data: netData,
            backgroundColor: netData.map((v) => (v >= 0 ? INCOME : EXPENSE)),
            hoverBackgroundColor: netData.map((v) => (v >= 0 ? "#047857" : "#b91c1c")),
            borderRadius: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        onClick: (evt, els) => {
          if (els.length) {
            const m = filteredMonths[els[0].index];
            if (m) {
              if (activeFilters.year === String(m.year) && activeFilters.month === String(m.month)) {
                activeFilters.year = "";
                activeFilters.month = "";
              } else {
                activeFilters.year = String(m.year);
                activeFilters.month = String(m.month);
              }
              const yEl = document.getElementById("selYear");
              const mEl = document.getElementById("selMonth");
              if (yEl) yEl.value = activeFilters.year;
              if (mEl) mEl.value = activeFilters.month;
              explorerCurrentPage = 1;
              renderAll();
            }
          }
        },
        onHover: (evt, els) => {
          evt.native.target.style.cursor = els.length ? "pointer" : "default";
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            ...tooltipBase,
            callbacks: {
              title: (items) => {
                if (!items.length) return "";
                const m = filteredMonths[items[0].dataIndex];
                return m ? `${monthNames[m.month - 1]} ${m.year} (${m.month_year})` : items[0].label;
              },
              label: (c) => {
                const m = filteredMonths[c.dataIndex];
                const net = c.parsed.y;
                const status = net >= 0 ? "Net Surplus" : "Net Deficit";
                return [
                  ` ${status}: ${net >= 0 ? "+" : ""}${fmtINRFull(net)}`,
                  ` Income: ${fmtINRFull(m.income)} · Expense: ${fmtINRFull(m.expense)}`,
                ];
              },
              footer: () => "(Click bar to filter by this month)",
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { font: { size: 10.5 }, color: "#475569", maxTicksLimit: 12 },
          },
          y: {
            grid: { color: RULE },
            ticks: { font: { size: 11 }, color: "#475569", callback: (v) => fmtINR(v) },
          },
        },
      },
    });
  }

  // 16. Chart 7: Year-over-Year Spend Comparison
  function makeYoY(filteredMonths) {
    destroyChart("chartYoY");
    const canvas = document.getElementById("chartYoY");
    if (!canvas) return;

    const yearlyExp = {};
    filteredMonths.forEach((m) => {
      yearlyExp[m.year] = (yearlyExp[m.year] || 0) + m.expense;
    });
    const years = Object.keys(yearlyExp).sort();

    charts.chartYoY = new Chart(canvas, {
      type: "bar",
      data: {
        labels: years,
        datasets: [
          {
            data: years.map((y) => Math.round(yearlyExp[y])),
            backgroundColor: years.map((y) => (y === activeFilters.year ? GOLD : EXPENSE)),
            hoverBackgroundColor: years.map((y) => (y === activeFilters.year ? "#b45309" : "#b91c1c")),
            borderRadius: 4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        onClick: (evt, els) => {
          if (els.length) {
            const y = years[els[0].index];
            setToolbarFilter("year", y);
          }
        },
        onHover: (evt, els) => {
          evt.native.target.style.cursor = els.length ? "pointer" : "default";
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            ...tooltipBase,
            callbacks: {
              title: (items) => (items.length ? `Calendar Year ${items[0].label}` : ""),
              label: (c) => {
                const curr = c.parsed.y;
                const idx = c.dataIndex;
                const lines = [` Total Expense: ${fmtINRFull(curr)}`];
                if (idx > 0) {
                  const prev = years.map((y) => Math.round(yearlyExp[y]))[idx - 1];
                  if (prev > 0) {
                    const change = (((curr - prev) / prev) * 100).toFixed(1);
                    lines.push(` YoY Change vs ${years[idx - 1]}: ${change >= 0 ? "+" : ""}${change}%`);
                  }
                }
                return lines;
              },
              footer: (items) =>
                items.length
                  ? `(Click to ${activeFilters.year === items[0].label ? "clear" : "filter by"} Year ${items[0].label})`
                  : "",
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { font: { size: 11.5, weight: "600" }, color: "#1e293b" },
          },
          y: {
            grid: { color: RULE },
            ticks: { font: { size: 11 }, color: "#475569", callback: (v) => fmtINR(v) },
          },
        },
      },
    });
  }

  // 17. Chart 8: Investment Allocation by Instrument
  function makeInvestDonut() {
    destroyChart("chartInvestDonut");
    const canvas = document.getElementById("chartInvestDonut");
    if (!canvas) return;

    const invCat = category_summary.find((c) => c.category === "Investment");
    const subcats = invCat && invCat.subcategories ? invCat.subcategories : [];
    const labels = subcats.map((s) => s.subcategory);
    const dataVals = subcats.map((s) => s.spend);
    const palette = ["#3b82f6", "#0ea5e9", "#06b6d4", "#14b8a6", "#10b981", "#6366f1", "#8b5cf6", "#d97706"];
    const total = dataVals.reduce((a, b) => a + b, 0);

    charts.chartInvestDonut = new Chart(canvas, {
      type: "doughnut",
      data: {
        labels,
        datasets: [
          {
            data: dataVals,
            backgroundColor: labels.map((_, i) => palette[i % palette.length]),
            borderWidth: 2,
            borderColor: CARD,
            hoverOffset: 8,
            hoverBorderWidth: 2,
            hoverBorderColor: "#ffffff",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "56%",
        onHover: (evt, els) => {
          evt.native.target.style.cursor = els.length ? "pointer" : "default";
        },
        plugins: {
          legend: {
            position: "bottom",
            labels: {
              boxWidth: 10,
              boxHeight: 10,
              font: { size: 10.5, weight: "500" },
              color: "#334155",
              padding: 10,
            },
          },
          tooltip: {
            ...tooltipBase,
            callbacks: {
              title: (items) => (items.length ? items[0].label : ""),
              label: (c) => {
                const pct = total > 0 ? ((c.parsed / total) * 100).toFixed(1) + "%" : "0%";
                return ` Amount: ${fmtINRFull(c.parsed)} (${pct} of investments)`;
              },
            },
          },
        },
      },
    });
  }

  // 18. Chart 9: Day-of-Week Spending Pattern
  function makeDayOfWeek() {
    destroyChart("chartDayOfWeek");
    const canvas = document.getElementById("chartDayOfWeek");
    if (!canvas) return;

    const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    const wkAvg = day_type_summary.weekday.average_daily_spend;
    const weAvg = day_type_summary.weekend.average_daily_spend;
    // Map Sunday & Saturday to weekend daily average, Mon-Fri to weekday daily average
    const dataVals = [weAvg, wkAvg, wkAvg, wkAvg, wkAvg, wkAvg, weAvg].map((v) => Math.round(v));

    charts.chartDayOfWeek = new Chart(canvas, {
      type: "bar",
      data: {
        labels: days,
        datasets: [
          {
            data: dataVals,
            backgroundColor: days.map((_, i) => (i === 0 || i === 6 ? GOLD : EXPENSE)),
            hoverBackgroundColor: days.map((_, i) => (i === 0 || i === 6 ? "#b45309" : "#b91c1c")),
            borderRadius: 4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        onClick: (evt, els) => {
          if (els.length) {
            const idx = els[0].index;
            const isWe = idx === 0 || idx === 6;
            setToolbarFilter("wknd", isWe ? "we" : "wk");
          }
        },
        onHover: (evt, els) => {
          evt.native.target.style.cursor = els.length ? "pointer" : "default";
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            ...tooltipBase,
            callbacks: {
              title: (items) => {
                if (!items.length) return "";
                const d = days[items[0].dataIndex];
                const fullMap = { Sun: "Sunday", Mon: "Monday", Tue: "Tuesday", Wed: "Wednesday", Thu: "Thursday", Fri: "Friday", Sat: "Saturday" };
                const fullName = fullMap[d] || d;
                const isWe = items[0].dataIndex === 0 || items[0].dataIndex === 6;
                return `${fullName} (${isWe ? "Weekend" : "Weekday"})`;
              },
              label: (c) => ` Daily Average Spend: ${fmtINRFull(c.parsed.y)} / day`,
              footer: (items) => {
                if (!items.length) return "";
                const isWe = items[0].dataIndex === 0 || items[0].dataIndex === 6;
                return `(Click to filter by ${isWe ? "Weekend" : "Weekday"})`;
              },
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { font: { size: 11.5, weight: "600" }, color: "#1e293b" },
          },
          y: {
            grid: { color: RULE },
            ticks: { font: { size: 11 }, color: "#475569", callback: (v) => fmtINR(v) },
          },
        },
      },
    });
  }

  // 19. Chart 10: Transaction Frequency vs Value by Category (Bubble)
  function makeFreqValue(filteredCats) {
    destroyChart("chartFreqValue");
    const canvas = document.getElementById("chartFreqValue");
    if (!canvas) return;

    const points = filteredCats.map((c) => {
      const avg = c.transaction_count > 0 ? c.total_spend / c.transaction_count : 0;
      return {
        x: c.transaction_count,
        y: Math.round(avg),
        r: Math.max(5, Math.min(26, Math.sqrt(c.total_spend) / 24)),
        cat: c.category,
        sum: c.total_spend,
      };
    });

    charts.chartFreqValue = new Chart(canvas, {
      type: "bubble",
      data: {
        datasets: [
          {
            data: points,
            backgroundColor: points.map((p) => (p.cat === drillCat ? GOLD + "DD" : EXPENSE + "BB")),
            hoverBackgroundColor: points.map((p) => (p.cat === drillCat ? GOLD : EXPENSE)),
            borderColor: points.map((p) => (p.cat === drillCat ? "#b45309" : "#b91c1c")),
            borderWidth: 1,
            hoverBorderWidth: 2,
            hoverBorderColor: "#0f172a",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        onClick: (evt, els) => {
          if (els.length) {
            const pt = points[els[0].index];
            if (pt) {
              drillCat = drillCat === pt.cat ? null : pt.cat;
              renderDrill();
              makeTopCat(filteredCats);
              makeFreqValue(filteredCats);
              const drillEl = document.getElementById("drillPanel");
              if (drillEl && typeof drillEl.scrollIntoView === "function" && drillCat) {
                drillEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
              }
            }
          }
        },
        onHover: (evt, els) => {
          evt.native.target.style.cursor = els.length ? "pointer" : "default";
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            ...tooltipBase,
            callbacks: {
              title: (items) => (items.length && items[0].raw ? items[0].raw.cat : ""),
              label: (c) => {
                const raw = c.raw;
                if (!raw) return [];
                const overallExp = kpis_overall.total_expense;
                const pct = overallExp > 0 ? ((raw.sum / overallExp) * 100).toFixed(1) + "%" : "0%";
                return [
                  ` Total Spend: ${fmtINRFull(raw.sum)} (${pct} of expenses)`,
                  ` Transaction Count: ${raw.x.toLocaleString()} txns`,
                  ` Average Spend: ${fmtINRFull(raw.y)} / transaction`,
                ];
              },
              footer: () => "(Click bubble to inspect category breakdown)",
            },
          },
        },
        scales: {
          x: {
            title: { display: true, text: "Transaction count →", font: { size: 11, weight: "600" }, color: "#334155" },
            grid: { color: RULE },
            ticks: { font: { size: 11 }, color: "#475569" },
          },
          y: {
            title: {
              display: true,
              text: "Avg transaction value (₹) →",
              font: { size: 11, weight: "600" },
              color: "#334155",
            },
            grid: { color: RULE },
            ticks: { font: { size: 11 }, color: "#475569", callback: (v) => fmtINR(v) },
          },
        },
      },
    });
  }

  // 20. Chart 11: Cumulative Net Position
  function makeCumulative(filteredMonths) {
    destroyChart("chartCumulative");
    const canvas = document.getElementById("chartCumulative");
    if (!canvas) return;

    let running = 0;
    const labels = [];
    const dataVals = [];

    filteredMonths.forEach((m) => {
      running += (m.income - m.expense - m.transfers);
      labels.push(m.month_year);
      dataVals.push(Math.round(running));
    });

    charts.chartCumulative = new Chart(canvas, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            data: dataVals,
            borderColor: INVEST,
            backgroundColor: INVEST + "22",
            fill: true,
            pointRadius: 0,
            pointHoverRadius: 6,
            pointHoverBackgroundColor: INVEST,
            pointHoverBorderColor: "#ffffff",
            pointHoverBorderWidth: 2,
            borderWidth: 2.2,
            tension: 0.15,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        onClick: (evt, els) => {
          if (els.length) {
            const idx = els[0].index;
            const m = filteredMonths[idx];
            if (m) {
              if (activeFilters.year === String(m.year) && activeFilters.month === String(m.month)) {
                activeFilters.year = "";
                activeFilters.month = "";
              } else {
                activeFilters.year = String(m.year);
                activeFilters.month = String(m.month);
              }
              const yEl = document.getElementById("selYear");
              const mEl = document.getElementById("selMonth");
              if (yEl) yEl.value = activeFilters.year;
              if (mEl) mEl.value = activeFilters.month;
              explorerCurrentPage = 1;
              renderAll();
            }
          }
        },
        onHover: (evt, els) => {
          evt.native.target.style.cursor = els.length ? "pointer" : "default";
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            ...tooltipBase,
            mode: "index",
            intersect: false,
            callbacks: {
              title: (items) => {
                if (!items.length) return "";
                const m = filteredMonths[items[0].dataIndex];
                return m ? `${monthNames[m.month - 1]} ${m.year} (${m.month_year})` : items[0].label;
              },
              label: (c) => ` Cumulative Net Position: ${c.parsed.y >= 0 ? "+" : ""}${fmtINRFull(c.parsed.y)}`,
              footer: () => "Running Total: Income − Expense − Transfers\n(Click to filter by this month)",
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { font: { size: 10.5 }, color: "#475569", maxTicksLimit: 12 },
          },
          y: {
            grid: { color: RULE },
            ticks: { font: { size: 11 }, color: "#475569", callback: (v) => fmtINR(v) },
          },
        },
      },
    });
  }

  // 21. Drilldown Aggregate Table (Category Subcategory Breakdown)
  function renderDrill() {
    const panel = document.getElementById("drillPanel");
    if (!panel) return;
    if (!drillCat) {
      panel.classList.remove("show");
      return;
    }

    const catObj = category_summary.find((c) => c.category === drillCat);
    if (!catObj || !catObj.subcategories || !catObj.subcategories.length) {
      panel.classList.remove("show");
      return;
    }

    panel.classList.add("show");
    const titleEl = document.getElementById("drillTitle");
    if (titleEl) {
      titleEl.textContent = `Category Breakdown · ${drillCat}`;
    }

    const body = document.getElementById("drillBody");
    if (!body) return;
    body.innerHTML = "";

    const sortedSubcats = [...catObj.subcategories].sort((a, b) => b.spend - a.spend);
    sortedSubcats.forEach((sub) => {
      const pct = catObj.total_spend > 0 ? ((sub.spend / catObj.total_spend) * 100).toFixed(1) + "%" : "—";
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td style="font-weight:500;">${sub.subcategory}</td>
        <td class="amt expense">${fmtINRFull(sub.spend)}</td>
        <td style="font-family:'Consolas','IBM Plex Mono',monospace;font-size:12.5px;">${sub.count.toLocaleString()}</td>
        <td style="font-family:'Consolas','IBM Plex Mono',monospace;font-size:12.5px;color:${MUTE};font-weight:500;">${pct}</td>
      `;
      body.appendChild(tr);
    });
  }

  // 22. Master Render Orchestrator
  function renderAll() {
    const filteredMonths = getFilteredMonths();
    const filteredCats = getFilteredCategories();
    const filteredModes = getFilteredPaymentModes();

    renderKPIs(filteredMonths, filteredCats);
    renderInsights(filteredMonths, filteredCats);

    if (typeof Chart === "undefined") {
      console.warn("Chart.js library is not yet loaded. Skipping chart rendering.");
      return;
    }

    makeTrend(filteredMonths);
    makeTypeDonut(filteredMonths);
    makeTopCat(filteredCats);
    makePaymentMode(filteredModes);
    makeWeekend();
    makeNetSavings(filteredMonths);
    makeYoY(filteredMonths);
    makeInvestDonut();
    makeDayOfWeek();
    makeFreqValue(filteredCats);
    makeCumulative(filteredMonths);
    renderDrill();
    renderExplorer(filteredCats, filteredMonths);
  }

  // ── Feature 1: Populate Compact Footer Attribution ─────────────────────────
  function populateAttribution() {
    const attrTextEl = document.getElementById("footerAttrText");
    if (attrTextEl) {
      attrTextEl.textContent = `Dataset Source: ${meta.dataset_source} · Period: ${meta.min_date} – ${meta.max_date} (${meta.total_calendar_days} calendar days) · Currency: ${meta.currency} (${meta.currency_symbol}) · Built By Girish Shenoy`;
    }
    const disclaimerEl = document.getElementById("footerDisclaimer");
    if (disclaimerEl) {
      disclaimerEl.textContent = "This dashboard presents pre-aggregated analytical summaries for portfolio and educational review. Zero transaction-level records, individual purchase amounts, or personal notes are published.";
    }
  }

  // ── Feature 2: Aggregated Data Explorer with 5-Record Pagination ──────────
  // Derives category-level aggregated rows from category_summary,
  // optionally filtered by activeFilters.year (applied via monthly_series share)
  // and activeFilters.cat. Strictly zero transaction-level records.

  function getExplorerRows(filteredCats, filteredMonths) {
    // Compute total expense for the current month filter to recalculate pct shares.
    const filteredExpenseTotal = filteredMonths.reduce((s, m) => s + m.expense, 0);

    // When a time filter is active we scale each category's spend proportionally
    // (the payload does not carry per-category-per-month breakdowns, so we use the
    //  overall ratio of filtered-months expense to total expense as a scalar).
    const overallExpenseTotal = kpis_overall.total_expense;
    const timeScalar = (overallExpenseTotal > 0 && (activeFilters.year || activeFilters.month))
      ? filteredExpenseTotal / overallExpenseTotal
      : 1;

    return filteredCats.map((c) => {
      const scaledSpend = c.total_spend * timeScalar;
      const scaledCount = Math.round(c.transaction_count * timeScalar);
      const scaledTotal = overallExpenseTotal > 0 ? filteredExpenseTotal : overallExpenseTotal;
      const pct = scaledTotal > 0 ? (scaledSpend / scaledTotal * 100) : 0;
      const avgPerTxn = scaledCount > 0 ? scaledSpend / scaledCount : 0;
      return {
        category: c.category,
        spend: scaledSpend,
        count: scaledCount,
        pct: pct,
        avg: avgPerTxn,
      };
    }).sort((a, b) => b.spend - a.spend);
  }

  function renderExplorer(filteredCats, filteredMonths) {
    const body = document.getElementById("explorerBody");
    const noteEl = document.getElementById("explorerNote");
    const subtitleEl = document.getElementById("explorerSubtitle");
    const infoEl = document.getElementById("paginationInfo");
    const prevBtn = document.getElementById("prevPageBtn");
    const nextBtn = document.getElementById("nextPageBtn");
    if (!body) return;

    const allRows = getExplorerRows(filteredCats, filteredMonths);
    const totalRecords = allRows.length;
    const totalPages = Math.max(1, Math.ceil(totalRecords / EXPLORER_PAGE_SIZE));

    // Clamp pagination
    if (explorerCurrentPage > totalPages) explorerCurrentPage = totalPages;
    if (explorerCurrentPage < 1) explorerCurrentPage = 1;

    // Slice 5 records for display
    const startIndex = (explorerCurrentPage - 1) * EXPLORER_PAGE_SIZE;
    const endIndex = Math.min(startIndex + EXPLORER_PAGE_SIZE, totalRecords);
    const pageRows = totalRecords > 0 ? allRows.slice(startIndex, endIndex) : [];

    // Update subtitle to reflect active filters
    const parts = [];
    if (activeFilters.year) parts.push(`Year: ${activeFilters.year}`);
    if (activeFilters.month) parts.push(`Month: ${monthNames[+activeFilters.month - 1]}`);
    if (activeFilters.cat) parts.push(`Category: ${activeFilters.cat}`);
    const filterLabel = parts.length ? parts.join(" · ") : "All periods, all categories";
    if (subtitleEl) subtitleEl.textContent = `Category-level aggregated spend · ${filterLabel}`;

    // Render 5 visible table rows
    body.innerHTML = "";
    if (pageRows.length === 0) {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td colspan="5" style="text-align:center;color:${MUTE};padding:16px;">No data matches the current filter selection.</td>`;
      body.appendChild(tr);
    } else {
      pageRows.forEach((r) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td style="font-weight:500;">${r.category}</td>
          <td class="amt expense">${fmtINRFull(r.spend)}</td>
          <td style="font-family:'Consolas','IBM Plex Mono',monospace;font-size:12.5px;">${r.count.toLocaleString()}</td>
          <td style="font-family:'Consolas','IBM Plex Mono',monospace;font-size:12.5px;font-weight:500;">${r.pct.toFixed(1)}%</td>
          <td class="amt">${fmtINRFull(r.avg)}</td>
        `;
        body.appendChild(tr);
      });
    }

    // Update pagination controls
    const pageIndEl = document.getElementById("pageIndicator");
    if (infoEl) {
      if (totalRecords === 0) {
        infoEl.textContent = "Showing 0 categories";
      } else if (startIndex + 1 === endIndex) {
        infoEl.textContent = `Showing ${endIndex} of ${totalRecords} ${totalRecords === 1 ? "category" : "categories"}`;
      } else {
        infoEl.textContent = `Showing ${startIndex + 1}–${endIndex} of ${totalRecords} categories`;
      }
    }
    if (pageIndEl) {
      pageIndEl.textContent = totalRecords === 0 ? "0 / 0" : `${explorerCurrentPage} / ${totalPages}`;
    }
    if (prevBtn) prevBtn.disabled = (explorerCurrentPage <= 1 || totalRecords === 0);
    if (nextBtn) nextBtn.disabled = (explorerCurrentPage >= totalPages || totalRecords === 0);

    // Footer note
    const timeNote = (activeFilters.year || activeFilters.month) ? " · Spend figures are proportionally scaled to the selected time window." : "";
    if (noteEl) {
      noteEl.textContent = `${totalRecords} categor${totalRecords === 1 ? "y" : "ies"} · Aggregated data only — no individual transaction records${timeNote}`;
    }
  }

  // ── Feature 3: Aggregated CSV Export (Full Dataset) ───────────────────────
  function buildCsvContent(filteredCats, filteredMonths) {
    // Note: getExplorerRows returns all matching records, independent of visible page slice.
    const rows = getExplorerRows(filteredCats, filteredMonths);

    // Header row
    const headers = ["Category", "Total Spend (INR)", "Transaction Count", "Pct of Expenses", "Avg per Transaction (INR)"];
    const lines = [headers.join(",")];

    rows.forEach((r) => {
      const row = [
        `"${r.category.replace(/"/g, '""')}"`,
        r.spend.toFixed(2),
        r.count,
        r.pct.toFixed(2),
        r.avg.toFixed(2),
      ];
      lines.push(row.join(","));
    });

    // Metadata footer rows (two blank lines then meta)
    lines.push("");
    lines.push("");
    lines.push(`"# Dataset","${meta.dataset_source}"`);
    lines.push(`"# Period","${meta.min_date} to ${meta.max_date}"`);
    lines.push(`"# Currency","${meta.currency}"`);
    lines.push(`"# Privacy","${meta.publication_model}"`);
    if (activeFilters.year) lines.push(`"# Filter: Year","${activeFilters.year}"`);
    if (activeFilters.month) lines.push(`"# Filter: Month","${monthNames[+activeFilters.month - 1]}"`);
    if (activeFilters.cat) lines.push(`"# Filter: Category","${activeFilters.cat}"`);
    lines.push(`"# Note","Transfers-out are excluded from expense calculations in this export."`);

    return lines.join("\r\n");
  }

  function downloadCsv() {
    const filteredCats = getFilteredCategories();
    const filteredMonths = getFilteredMonths();
    const csv = buildCsvContent(filteredCats, filteredMonths);
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");

    // Build a meaningful filename
    const yearPart = activeFilters.year ? `_${activeFilters.year}` : "";
    const catPart = activeFilters.cat ? `_${activeFilters.cat.replace(/[^a-z0-9]/gi, "-")}` : "";
    a.download = `expense_summary${yearPart}${catPart}.csv`;
    a.href = url;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  const exportBtn = document.getElementById("exportCsvBtn");
  if (exportBtn) {
    exportBtn.addEventListener("click", downloadCsv);
  }

  // Pagination navigation listeners
  const prevBtn = document.getElementById("prevPageBtn");
  if (prevBtn) {
    prevBtn.addEventListener("click", () => {
      if (explorerCurrentPage > 1) {
        explorerCurrentPage--;
        renderExplorer(getFilteredCategories(), getFilteredMonths());
      }
    });
  }

  const nextBtn = document.getElementById("nextPageBtn");
  if (nextBtn) {
    nextBtn.addEventListener("click", () => {
      const allRows = getExplorerRows(getFilteredCategories(), getFilteredMonths());
      const totalPages = Math.max(1, Math.ceil(allRows.length / EXPLORER_PAGE_SIZE));
      if (explorerCurrentPage < totalPages) {
        explorerCurrentPage++;
        renderExplorer(getFilteredCategories(), getFilteredMonths());
      }
    });
  }

  // Initial execution when DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      populateAttribution();
      renderAll();
    });
  } else {
    populateAttribution();
    renderAll();
  }
})();
