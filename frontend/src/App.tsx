import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowDownUp,
  BadgeCheck,
  BookOpenCheck,
  Check,
  ChevronDown,
  CircleHelp,
  ClipboardCheck,
  CloudLightning,
  Database,
  Download,
  ExternalLink,
  FileDiff,
  FileJson,
  Filter,
  HeartPulse,
  History,
  Info,
  Layers3,
  ListChecks,
  Map,
  Menu,
  PanelRightClose,
  PanelRightOpen,
  Plus,
  RefreshCw,
  Save,
  Search,
  ShieldAlert,
  SlidersHorizontal,
  Table2,
  X,
} from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  type SortingState,
  useReactTable,
} from "@tanstack/react-table";
import { apiClient } from "./api/client";
import { IndiaMap } from "./components/IndiaMap";
import type {
  CapabilityId,
  DocumentaryState,
  ExternalVerificationResult,
  Facility,
  GeographyOption,
  RegionResult,
  Scenario,
  VerificationItem,
} from "./types";

type ViewId = "planner" | "scenarios" | "verification";

const stateTone: Record<DocumentaryState, string> = {
  strong: "tone-strong",
  low: "tone-low",
  validation: "tone-validation",
  mixed: "tone-mixed",
  insufficient: "tone-insufficient",
  unavailable: "tone-unavailable",
};

const columnHelper = createColumnHelper<RegionResult>();

function formatPercent(value: number) {
  return `${Math.round(value * 100)}%`;
}

function traceSuffix(traceId: string) {
  return traceId.slice(-8);
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "The service request failed.";
}

function spreadsheetSafeCell(value: string) {
  return /^[=+\-@]/.test(value.trimStart()) ? `'${value}` : value;
}

function csvCell(value: string) {
  return `"${spreadsheetSafeCell(value).replaceAll('"', '""')}"`;
}

function downloadFile(filename: string, value: string, type: string) {
  const url = URL.createObjectURL(new Blob([value], { type }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function App() {
  const queryClient = useQueryClient();
  const [view, setView] = useState<ViewId>("planner");
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [capabilityId, setCapabilityId] = useState<CapabilityId>("maternal_emergency_documentation");
  const [geography, setGeography] = useState("district:br:darbhanga");
  const [radiusKm, setRadiusKm] = useState(25);
  const [selectedRegionId, setSelectedRegionId] = useState("district:br:darbhanga");
  const [selectedFacilityId, setSelectedFacilityId] = useState("b69b988a-1179-44df-8349-e0d632ebfb83");
  const [rightRailOpen, setRightRailOpen] = useState(true);
  const [crisisEnabled, setCrisisEnabled] = useState(false);
  const [healthOpen, setHealthOpen] = useState(false);
  const [saveOpen, setSaveOpen] = useState(false);
  const [scenarioName, setScenarioName] = useState("Darbhanga evidence review");
  const [scenarioNotes, setScenarioNotes] = useState("");
  const [reopenedScenario, setReopenedScenario] = useState<Scenario | null>(null);

  const healthQuery = useQuery({ queryKey: ["health"], queryFn: apiClient.getHealth });
  const capabilitiesQuery = useQuery({ queryKey: ["capabilities"], queryFn: apiClient.getCapabilities });
  const geographiesQuery = useQuery({ queryKey: ["geographies"], queryFn: apiClient.getGeographies });
  const resultsQuery = useQuery({
    queryKey: ["results", capabilityId, geography, radiusKm],
    queryFn: () =>
      apiClient.queryDocumentaryEvidence({ capabilityId, geography, radiusKm }),
    placeholderData: (previous) => previous,
  });
  const surveyQuery = useQuery({
    queryKey: ["survey", "district:br:darbhanga"],
    queryFn: () => apiClient.getSurveyContext("district:br:darbhanga"),
  });
  const facilityQuery = useQuery({
    queryKey: ["facility", selectedFacilityId, capabilityId],
    queryFn: () => apiClient.getFacility(selectedFacilityId, capabilityId),
  });
  const queueQuery = useQuery({
    queryKey: ["verification"],
    queryFn: apiClient.getVerificationQueue,
  });
  const scenariosQuery = useQuery({
    queryKey: ["scenarios"],
    queryFn: apiClient.listScenarios,
  });
  const saveScenarioMutation = useMutation({
    mutationFn: apiClient.saveScenario,
    onSuccess: (scenario) => {
      queryClient.setQueryData<Scenario[]>(["scenarios"], (current = []) => [
        scenario,
        ...current.filter((item) => item.id !== scenario.id),
      ]);
      setSaveOpen(false);
      setReopenedScenario(scenario);
    },
  });

  const results = resultsQuery.data ?? [];
  const selectedRegion =
    results.find((region) => region.id === selectedRegionId) ?? results[0];
  const selectedFacility = facilityQuery.data;
  const activeError =
    view === "planner"
      ? resultsQuery.error ??
        capabilitiesQuery.error ??
        geographiesQuery.error ??
        surveyQuery.error ??
        facilityQuery.error
      : view === "verification"
        ? queueQuery.error
        : scenariosQuery.error;

  useEffect(() => {
    if (!results.length) return;
    if (!results.some((region) => region.id === selectedRegionId)) {
      setSelectedRegionId(results[0].id);
    }
  }, [results, selectedRegionId]);

  useEffect(() => {
    const available = selectedRegion?.facilityOptions ?? [];
    if (available.length && !available.some((facility) => facility.id === selectedFacilityId)) {
      setSelectedFacilityId(available[0].id);
    }
  }, [selectedFacilityId, selectedRegion]);

  const selectRegion = (region: RegionResult) => {
    setSelectedRegionId(region.id);
    setRightRailOpen(true);
    const nextFacility =
      region.facilityOptions.find((facility) => !facility.contributionReason.startsWith("Excluded"))?.id ??
      region.facilityOptions[0]?.id;
    if (!nextFacility) return;
    setSelectedFacilityId(nextFacility);
  };

  const saveCurrentScenario = () => {
    saveScenarioMutation.mutate({
      name: scenarioName.trim() || "Untitled planning scenario",
      capabilityId,
      geography,
      radiusKm,
      selectedRegionIds: selectedRegion ? [selectedRegion.id] : [],
      facilityIds: selectedFacility ? [selectedFacility.id] : [],
      notes: scenarioNotes,
      sourceBundleId: "virtue-foundation-2026-07",
      policyVersion: `${capabilityId}-0.2.0`,
      evidenceSnapshotId: "evidence-2026-07-19T0800Z",
    });
  };

  const openSaveDialog = () => {
    saveScenarioMutation.reset();
    setSaveOpen(true);
  };

  const navigation = [
    { id: "planner" as const, label: "Planner", icon: Map },
    { id: "scenarios" as const, label: "Scenarios", icon: Layers3 },
    { id: "verification" as const, label: "Verification Queue", icon: ListChecks },
  ];

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand-block">
          <button
            className="icon-button mobile-only"
            type="button"
            aria-label="Open navigation"
            onClick={() => setMobileNavOpen((value) => !value)}
          >
            <Menu size={20} />
          </button>
          <div className="brand-mark" aria-hidden="true"><HeartPulse size={20} /></div>
          <div>
            <strong>CareAxiom</strong>
            <span>Evidence-grounded planning workspace</span>
          </div>
        </div>
        <div className="header-actions">
          <span className="planning-boundary">
            <ShieldAlert size={15} aria-hidden="true" />
            Planning support only
          </span>
          <button
            className={`health-button health-${healthQuery.data?.state ?? "unavailable"}`}
            type="button"
            onClick={() => setHealthOpen((value) => !value)}
            aria-expanded={healthOpen}
          >
            <Activity size={15} aria-hidden="true" />
            {healthQuery.data?.state === "healthy" ? "Systems healthy" : "Degraded mode"}
          </button>
        </div>
      </header>

      {healthOpen && <HealthPanel health={healthQuery.data} onClose={() => setHealthOpen(false)} />}

      <div className="workspace">
        <aside className={`side-nav ${mobileNavOpen ? "is-open" : ""}`}>
          <nav aria-label="Primary navigation">
            {navigation.map((item) => (
              <button
                key={item.id}
                className={view === item.id ? "nav-item is-active" : "nav-item"}
                type="button"
                onClick={() => {
                  setView(item.id);
                  setMobileNavOpen(false);
                }}
              >
                <item.icon size={18} aria-hidden="true" />
                <span>{item.label}</span>
              </button>
            ))}
          </nav>
          <div className="nav-footer">
            <span>Single-team demo</span>
            <small>Referral Copilot off</small>
          </div>
        </aside>

        <main className="main-content">
          {activeError && (
            <div className="service-error" role="alert">
              <AlertCircle size={18} />
              <div>
                <strong>Service request failed</strong>
                <span>{errorMessage(activeError)} No demo result was substituted.</span>
              </div>
            </div>
          )}
          {view === "planner" && (
            <PlannerView
              capabilityId={capabilityId}
              geography={geography}
              radiusKm={radiusKm}
              capabilities={capabilitiesQuery.data ?? []}
              geographies={geographiesQuery.data ?? []}
              results={results}
              selectedRegion={selectedRegion}
              selectedFacility={selectedFacility}
              selectedFacilityId={selectedFacilityId}
              survey={surveyQuery.data}
              rightRailOpen={rightRailOpen}
              crisisEnabled={crisisEnabled}
              isFetching={resultsQuery.isFetching}
              onCapabilityChange={(value) => {
                setCapabilityId(value);
                setSelectedFacilityId(
                  "b69b988a-1179-44df-8349-e0d632ebfb83",
                );
              }}
              onGeographyChange={setGeography}
              onRadiusChange={setRadiusKm}
              onRegionSelect={selectRegion}
              onFacilityChange={setSelectedFacilityId}
              onRightRailToggle={() => setRightRailOpen((value) => !value)}
              onCrisisToggle={() => setCrisisEnabled((value) => !value)}
              onSave={openSaveDialog}
              onOpenVerification={() => setView("verification")}
            />
          )}
          {view === "verification" && (
            <VerificationView
              items={queueQuery.data ?? []}
              onOpenFacility={(facilityId) => {
                setSelectedFacilityId(facilityId);
                setRightRailOpen(true);
                setView("planner");
              }}
            />
          )}
          {view === "scenarios" && (
            <ScenariosView
              scenarios={scenariosQuery.data ?? []}
              reopenedScenario={reopenedScenario}
              onCreate={openSaveDialog}
              onReopen={(scenario) => {
                setCapabilityId(scenario.capabilityId);
                setGeography(scenario.geography);
                setRadiusKm(scenario.radiusKm);
                setSelectedRegionId(scenario.selectedRegionIds[0] ?? "district:br:darbhanga");
                setSelectedFacilityId(scenario.facilityIds[0] ?? "b69b988a-1179-44df-8349-e0d632ebfb83");
                setReopenedScenario(scenario);
                setView("planner");
              }}
              onCompare={setReopenedScenario}
            />
          )}
        </main>
      </div>

      {saveOpen && (
        <div className="modal-backdrop" role="presentation" onMouseDown={() => setSaveOpen(false)}>
          <section
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="save-scenario-title"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="panel-heading">
              <div>
                <span className="eyebrow">Immutable snapshot</span>
                <h2 id="save-scenario-title">Save planning scenario</h2>
              </div>
              <button className="icon-button" type="button" aria-label="Close" onClick={() => setSaveOpen(false)}>
                <X size={18} />
              </button>
            </div>
            <label className="field">
              <span>Name</span>
              <input value={scenarioName} onChange={(event) => setScenarioName(event.target.value)} />
            </label>
            <label className="field">
              <span>Decision notes</span>
              <textarea
                rows={4}
                value={scenarioNotes}
                onChange={(event) => setScenarioNotes(event.target.value)}
                placeholder="Record assumptions, validation needs, and decision rationale."
              />
            </label>
            <div className="snapshot-summary">
              <span>{geography}</span>
              <span>{radiusKm} km radius</span>
              <span>{selectedRegion?.documentaryLabel}</span>
            </div>
            {saveScenarioMutation.isError && (
              <div className="service-error compact" role="alert">
                <AlertCircle size={17} />
                <div>
                  <strong>Scenario was not saved</strong>
                  <span>{errorMessage(saveScenarioMutation.error)}</span>
                </div>
              </div>
            )}
            <div className="modal-actions">
              <button className="secondary-button" type="button" onClick={() => setSaveOpen(false)}>Cancel</button>
              <button
                className="primary-button"
                type="button"
                onClick={saveCurrentScenario}
                disabled={saveScenarioMutation.isPending}
              >
                <Save size={16} />
                {saveScenarioMutation.isPending ? "Saving…" : "Save scenario"}
              </button>
            </div>
          </section>
        </div>
      )}

      <div className="sr-only" aria-live="polite">
        {selectedRegion
          ? `${selectedRegion.name} selected. ${selectedRegion.documentaryLabel}.`
          : "No region selected."}
      </div>
    </div>
  );
}

interface PlannerViewProps {
  capabilityId: CapabilityId;
  geography: string;
  radiusKm: number;
  capabilities: Array<{ id: CapabilityId; label: string; description: string }>;
  geographies: GeographyOption[];
  results: RegionResult[];
  selectedRegion?: RegionResult;
  selectedFacility?: Facility;
  selectedFacilityId: string;
  survey?: Awaited<ReturnType<typeof apiClient.getSurveyContext>>;
  rightRailOpen: boolean;
  crisisEnabled: boolean;
  isFetching: boolean;
  onCapabilityChange: (value: CapabilityId) => void;
  onGeographyChange: (value: string) => void;
  onRadiusChange: (value: number) => void;
  onRegionSelect: (region: RegionResult) => void;
  onFacilityChange: (facilityId: string) => void;
  onRightRailToggle: () => void;
  onCrisisToggle: () => void;
  onSave: () => void;
  onOpenVerification: () => void;
}

function PlannerView(props: PlannerViewProps) {
  const [sorting, setSorting] = useState<SortingState>([{ id: "priority", desc: true }]);
  const columns = useMemo(
    () => [
      columnHelper.accessor("name", {
        header: "Postal reference",
        cell: (info) => (
          <div className="table-primary">
            <strong>{info.row.original.name}</strong>
            <span>{info.row.original.district}, {info.row.original.state}</span>
          </div>
        ),
      }),
      columnHelper.accessor("documentaryState", {
        header: "Documentary result",
        cell: (info) => (
          <span className={`result-label ${stateTone[info.getValue()]}`}>
            {info.row.original.documentaryLabel}
          </span>
        ),
      }),
      columnHelper.accessor("supportedFacilities", {
        header: "Supported / observed",
        cell: (info) => `${info.getValue()} / ${info.row.original.observedFacilities}`,
      }),
      columnHelper.accessor("assessability", {
        header: "Assessability",
        cell: (info) => formatPercent(info.getValue()),
      }),
      columnHelper.accessor("priority", {
        header: "Priority",
        cell: (info) => (
          <span className="priority-value">{Math.round(info.getValue() * 100)}</span>
        ),
      }),
    ],
    [],
  );
  const table = useReactTable({
    data: props.results,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <div className={`planner-layout ${props.rightRailOpen ? "" : "rail-collapsed"}`}>
      <section className="planner-main">
        <div className="page-heading">
          <div>
            <span className="eyebrow">Default workspace</span>
            <h1>Planner</h1>
            <p>Find weak nearby documentary support without treating missing records as missing care.</p>
          </div>
          <div className="page-actions">
            <button
              className={props.crisisEnabled ? "secondary-button is-active" : "secondary-button"}
              type="button"
              onClick={props.onCrisisToggle}
              aria-pressed={props.crisisEnabled}
            >
              <CloudLightning size={16} />
              Crisis overlay
            </button>
            <button className="primary-button" type="button" onClick={props.onSave}>
              <Save size={16} />
              Save scenario
            </button>
          </div>
        </div>

        <section className="control-bar" aria-label="Planner controls">
          <label className="control-field capability-control">
            <span><Search size={14} />Capability</span>
            <select
              value={props.capabilityId}
              onChange={(event) => props.onCapabilityChange(event.target.value as CapabilityId)}
            >
              {props.capabilities.map((capability) => (
                <option key={capability.id} value={capability.id}>{capability.label}</option>
              ))}
            </select>
          </label>
          <label className="control-field">
            <span><Map size={14} />Geography</span>
            <select value={props.geography} onChange={(event) => props.onGeographyChange(event.target.value)}>
              {props.geographies.map((item) => (
                <option key={item.id} value={item.id} disabled={!item.selectable}>
                  {item.name}{item.state && item.name !== item.state ? `, ${item.state}` : ""}
                  {!item.selectable ? " — unavailable" : ""}
                </option>
              ))}
            </select>
          </label>
          <fieldset className="radius-control">
            <legend><SlidersHorizontal size={14} />Planning radius</legend>
            <div className="segmented-control">
              {[10, 25, 50].map((radius) => (
                <button
                  key={radius}
                  type="button"
                  className={props.radiusKm === radius ? "is-active" : ""}
                  onClick={() => props.onRadiusChange(radius)}
                  aria-pressed={props.radiusKm === radius}
                >
                  {radius} km
                </button>
              ))}
            </div>
          </fieldset>
          <div className="assumption-note">
            <Info size={15} />
            Straight-line planning radius; not travel time.
          </div>
        </section>

        {props.crisisEnabled && (
          <div className="crisis-banner">
            <AlertTriangle size={17} />
            <div>
              <strong>Demo flood extent · uploaded geometry</strong>
              <span>Source time: July 19, 2026 08:00 MYT · Static demo · Core planner remains independent</span>
            </div>
          </div>
        )}

        <div className="map-stack">
          <IndiaMap
            regions={props.results}
            selectedId={props.selectedRegion?.id ?? ""}
            crisisEnabled={props.crisisEnabled}
            onSelect={props.onRegionSelect}
          />
          {props.isFetching && <div className="refresh-indicator"><RefreshCw size={15} />Updating results</div>}
        </div>

        <section className="results-section">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Accessible map alternative</span>
              <h2>Planning results</h2>
            </div>
            <span className="result-count"><Table2 size={15} />{props.results.length} origins</span>
          </div>
          <div className="table-scroll">
            <table>
              <thead>
                {table.getHeaderGroups().map((headerGroup) => (
                  <tr key={headerGroup.id}>
                    {headerGroup.headers.map((header) => (
                      <th key={header.id}>
                        {header.isPlaceholder ? null : (
                          <button
                            type="button"
                            className="sort-button"
                            onClick={header.column.getToggleSortingHandler()}
                          >
                            {flexRender(header.column.columnDef.header, header.getContext())}
                            {header.column.getCanSort() && <ArrowDownUp size={13} />}
                          </button>
                        )}
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody>
                {table.getRowModel().rows.map((row) => (
                  <tr
                    key={row.id}
                    className={row.original.id === props.selectedRegion?.id ? "is-selected" : ""}
                    onClick={() => props.onRegionSelect(row.original)}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id}>
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </section>

      <button
        className="rail-toggle"
        type="button"
        aria-label={props.rightRailOpen ? "Close detail panel" : "Open detail panel"}
        onClick={props.onRightRailToggle}
      >
        {props.rightRailOpen ? <PanelRightClose size={18} /> : <PanelRightOpen size={18} />}
      </button>

      {props.rightRailOpen && props.selectedRegion && (
        <aside className="detail-rail" aria-label="Selected result details">
          <RegionSummary region={props.selectedRegion} />
          <SurveyPanel survey={props.survey} />
          {props.selectedFacility ? (
            <TrustDesk
              facility={props.selectedFacility}
              facilityId={props.selectedFacilityId}
              facilityOptions={props.selectedRegion.facilityOptions}
              onFacilityChange={props.onFacilityChange}
              onOpenVerification={props.onOpenVerification}
            />
          ) : (
            <section className="rail-section">
              <h2>Facility Trust Desk</h2>
              <p className="rail-subtitle">Facility evidence is unavailable until the service request succeeds.</p>
            </section>
          )}
        </aside>
      )}
    </div>
  );
}

function RegionSummary({ region }: { region: RegionResult }) {
  const materializationLabels = {
    pending: "Update pending",
    failed: "Update failed",
    blocked_dependency: "Update blocked",
  } as const;
  const materializationLabel =
    region.materializationState === "applied"
      ? null
      : materializationLabels[region.materializationState];
  return (
    <section className="rail-section">
      <div className="rail-kicker">
        <span className={`result-label ${stateTone[region.documentaryState]}`}>{region.documentaryLabel}</span>
        {materializationLabel && (
          <span
            className={`status-pill ${
              region.materializationState === "pending" ? "status-warning" : "status-danger"
            }`}
          >
            {materializationLabel}
          </span>
        )}
      </div>
      <h2>{region.name}</h2>
      <p className="rail-subtitle">{region.district}, {region.state}</p>
      <div className="metric-grid">
        <div><span>Supported records</span><strong>{region.supportedFacilities}</strong></div>
        <div><span>Observed records</span><strong>{region.observedFacilities}</strong></div>
        <div><span>Assessability</span><strong>{formatPercent(region.assessability)}</strong></div>
        <div><span>Priority</span><strong>{Math.round(region.priority * 100)}</strong></div>
      </div>
      <div className="definition-callout">
        <CircleHelp size={16} />
        <p>This result summarizes observed documentary evidence. It does not establish current service availability, capacity, or a medical desert.</p>
      </div>
      <dl className="compact-list">
        <div><dt>Postal method</dt><dd>{region.postalMethod}</dd></div>
        <div><dt>Ambiguity</dt><dd>{region.postalAmbiguity}</dd></div>
        <div><dt>Dispersion</dt><dd>{region.dispersionKm ? `${region.dispersionKm} km` : "Unavailable"}</dd></div>
        <div><dt>Trace</dt><dd><code>{traceSuffix(region.traceId)}</code></dd></div>
      </dl>
    </section>
  );
}

function SurveyPanel({ survey }: { survey?: PlannerViewProps["survey"] }) {
  if (!survey) return null;
  return (
    <section className="rail-section survey-panel">
      <div className="section-heading compact">
        <div>
          <span className="eyebrow">Separate context axis</span>
          <h2>NFHS district context</h2>
        </div>
        <Database size={18} />
      </div>
      <p className="survey-period">
        {survey.period}
        {survey.householdsSurveyed !== null ? ` · ${survey.householdsSurveyed} households surveyed` : ""}
      </p>
      <div className="survey-metrics">
        {survey.metrics.map((metric) => (
          <div key={metric.label}>
            <span>{metric.label}</span>
            <strong>{metric.qualifier === "suppressed_lt_25" ? "Unavailable" : metric.value}</strong>
            <small>{metric.qualifier === "standard" ? "Published estimate" : metric.qualifier}</small>
          </div>
        ))}
      </div>
      <p className="context-note"><Info size={14} />{survey.note}</p>
    </section>
  );
}

function TrustDesk({
  facility,
  facilityId,
  facilityOptions,
  onFacilityChange,
  onOpenVerification,
}: {
  facility: Facility;
  facilityId: string;
  facilityOptions: RegionResult["facilityOptions"];
  onFacilityChange: (facilityId: string) => void;
  onOpenVerification: () => void;
}) {
  const selectableFacilities = facilityOptions.length
    ? facilityOptions
    : [{ id: facility.id, name: facility.name, contributionReason: "Selected facility" }];
  return (
    <section className="rail-section trust-desk">
      <div className="section-heading compact">
        <div>
          <span className="eyebrow">Facility drill-down</span>
          <h2>Facility Trust Desk</h2>
        </div>
        <BookOpenCheck size={19} />
      </div>
      <label className="field compact-field">
        <span>Facility record</span>
        <select value={facilityId} onChange={(event) => onFacilityChange(event.target.value)}>
          {selectableFacilities.map((item) => (
            <option value={item.id} key={`${item.id}-${item.name}`}>{item.name}</option>
          ))}
        </select>
      </label>

      {facility.locationConflict && (
        <div className="location-conflict" role="alert">
          <AlertTriangle size={18} />
          <div>
            <strong>Location conflict</strong>
            <p>
              City: {facility.locationConflict.city} · Longitude: {facility.locationConflict.longitude} ·
              PIN mapping: {facility.locationConflict.pinDistrict}
            </p>
            <span>{facility.locationConflict.disposition}</span>
          </div>
        </div>
      )}

      <div className="facility-heading">
        <div>
          <h3>{facility.name}</h3>
          <p>{facility.location}</p>
        </div>
        <span className={facility.supportIndex === null ? "score-badge is-muted" : "score-badge"}>
          {facility.supportIndex ?? "N/A"}
        </span>
      </div>
      <div className="verdict-grid">
        <div><span>Machine verdict</span><strong>{facility.machineVerdict}</strong></div>
        <div><span>Human verdict</span><strong>{facility.humanVerdict ?? "No override"}</strong></div>
        <div><span>Support band</span><strong>{facility.supportBand}</strong></div>
        <div><span>Contradiction</span><strong>{facility.contradictionState}</strong></div>
      </div>

      <details open className="evidence-group">
        <summary>Evidence spans <ChevronDown size={15} /></summary>
        {facility.evidence.map((evidence) => (
          <article className={`evidence-item evidence-${evidence.polarity}`} key={evidence.id}>
            <div className="evidence-meta">
              <span>{evidence.sourceField}</span>
              {evidence.url ? (
                <a href={evidence.url} target="_blank" rel="noreferrer">
                  Source <ExternalLink size={12} />
                </a>
              ) : (
                <span className="source-unavailable">Source URL unavailable</span>
              )}
            </div>
            <blockquote>{evidence.text}</blockquote>
            <small>{evidence.publisher} · {evidence.sourceFamily} · {evidence.extractionVersion}</small>
          </article>
        ))}
      </details>

      <details className="evidence-group">
        <summary>Score factors <ChevronDown size={15} /></summary>
        <div className="factor-list">
          {facility.factors.map((factor) => (
            <div key={factor.label}>
              <span>{factor.label}</span>
              <div className="factor-track"><i style={{ width: `${(factor.value / factor.max) * 100}%` }} /></div>
              <strong>{factor.value}/{factor.max}</strong>
            </div>
          ))}
        </div>
      </details>

      <details className="evidence-group">
        <summary>Missing prerequisites and history <ChevronDown size={15} /></summary>
        <ul className="warning-list">
          {facility.missingPrerequisites.map((item) => <li key={item}>{item}</li>)}
        </ul>
        <div className="history-list">
          {facility.history.map((item) => (
            <div key={`${item.time}-${item.action}`}>
              <History size={14} />
              <p><strong>{item.action}</strong><span>{item.actor} · {item.time}</span><small>{item.reason}</small></p>
            </div>
          ))}
        </div>
      </details>

      <button className="secondary-button full-width" type="button" onClick={onOpenVerification}>
        <ClipboardCheck size={16} />
        Open in Verification Queue
      </button>
    </section>
  );
}

function VerificationView({
  items,
  onOpenFacility,
}: {
  items: VerificationItem[];
  onOpenFacility: (facilityId: string) => void;
}) {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState(items[0]?.id ?? "");
  const [reason, setReason] = useState("");
  const selected = items.find((item) => item.id === selectedId) ?? items[0];
  const externalEvidenceMutation = useMutation<ExternalVerificationResult>({
    mutationFn: () => apiClient.getExternalVerificationEvidence(selected.id),
  });
  const decisionMutation = useMutation({
    mutationFn: ({ status }: { status: VerificationItem["status"] }) =>
      apiClient.decideVerificationItem(selected, status, reason),
    onSuccess: (updated) => {
      queryClient.setQueryData<VerificationItem[]>(["verification"], (current = []) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
      setReason("");
    },
  });
  useEffect(() => {
    externalEvidenceMutation.reset();
    decisionMutation.reset();
  }, [selected?.id]);

  return (
    <div className="desk-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">Supporting review workflow</span>
          <h1>Data Readiness Desk</h1>
          <p>Review records by expected impact on planning decisions, not generic data-quality severity.</p>
        </div>
        <span className="formula-chip"><Filter size={14} />Priority formula v0.1</span>
      </div>
      <div className="queue-layout">
        <section className="queue-list" aria-label="Verification priority queue">
          <div className="section-heading compact">
            <h2>Verification Queue</h2>
            <span>{items.filter((item) => item.status === "open").length} open</span>
          </div>
          {items.map((item) => (
            <button
              key={item.id}
              type="button"
              className={item.id === selected?.id ? "queue-item is-selected" : "queue-item"}
              onClick={() => setSelectedId(item.id)}
            >
              <span className={`queue-priority ${item.priority >= 0.8 ? "is-high" : ""}`}>
                {Math.round(item.priority * 100)}
              </span>
              <span className="queue-copy">
                <strong>
                  {item.flag === "location_conflict" && <AlertTriangle size={15} />}
                  {item.facilityName}
                </strong>
                <span>{item.issue}</span>
                <small>{item.region} · {item.status.replace("_", " ")}</small>
              </span>
            </button>
          ))}
        </section>

        {selected && (
          <section className="decision-panel">
            {selected.flag === "location_conflict" && (
              <div className="location-conflict">
                <AlertTriangle size={18} />
                <div>
                  <strong>Location conflict</strong>
                  <p>This facility is excluded from confident planning results until reviewed.</p>
                </div>
              </div>
            )}
            <div className="panel-heading">
              <div>
                <span className="eyebrow">{selected.capability}</span>
                <h2>{selected.facilityName}</h2>
                <p>{selected.issue}</p>
              </div>
              <button className="secondary-button" type="button" onClick={() => onOpenFacility(selected.facilityId)}>
                <BookOpenCheck size={16} />Trust Desk
              </button>
            </div>
            <div className="impact-grid">
              <div><span>Expected impact</span><strong>{Math.round(selected.priority * 100)}/100</strong></div>
              <div><span>Regions affected</span><strong>{selected.affectedRegions}</strong></div>
              <div><span>Active scenarios</span><strong>{selected.scenarioReferences}</strong></div>
              <div><span>Queue age</span><strong>{selected.ageDays} days</strong></div>
            </div>
            <section className="review-evidence">
              <h3>Why this matters</h3>
              <p>{selected.whyItMatters}</p>
              <div className="trace-line"><Activity size={14} />Trace <code>{selected.traceId}</code></div>
              <button
                className="secondary-button external-evidence-button"
                type="button"
                onClick={() => externalEvidenceMutation.mutate()}
                disabled={externalEvidenceMutation.isPending}
              >
                <Search size={16} />
                {externalEvidenceMutation.isPending
                  ? "Checking sources"
                  : "Check external sources"}
              </button>
              {externalEvidenceMutation.data && (
                <div className="external-evidence-results" aria-live="polite">
                  <div>
                    <strong>
                      {externalEvidenceMutation.data.mode === "live"
                        ? "Live Tavily leads"
                        : "Cached verification"}
                    </strong>
                    <code>{traceSuffix(externalEvidenceMutation.data.traceId)}</code>
                  </div>
                  <p>{externalEvidenceMutation.data.limitation}</p>
                  {externalEvidenceMutation.data.results.map((result) => (
                    <a
                      href={result.url}
                      target="_blank"
                      rel="noreferrer"
                      key={result.url}
                    >
                      <span>{result.title ?? result.url}</span>
                      <ExternalLink size={13} />
                    </a>
                  ))}
                </div>
              )}
              {externalEvidenceMutation.isError && (
                <div className="service-error compact" role="alert">
                  <AlertCircle size={17} />
                  <div>
                    <strong>External verification failed</strong>
                    <span>{errorMessage(externalEvidenceMutation.error)}</span>
                  </div>
                </div>
              )}
            </section>
            <label className="field">
              <span>Decision reason</span>
              <textarea
                rows={5}
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                placeholder="Cite the source or explain why the item remains unresolved."
              />
            </label>
            <div className="decision-actions">
              <button type="button" className="secondary-button" disabled={decisionMutation.isPending} onClick={() => decisionMutation.mutate({ status: "deferred" })}>
                Defer
              </button>
              <button type="button" className="secondary-button" disabled={decisionMutation.isPending} onClick={() => decisionMutation.mutate({ status: "unresolved" })}>
                Mark unresolved
              </button>
              <button type="button" className="primary-button" disabled={decisionMutation.isPending} onClick={() => decisionMutation.mutate({ status: "resolved" })}>
                <Check size={16} />Confirm decision
              </button>
            </div>
            {decisionMutation.isSuccess && (
              <div className="success-message"><BadgeCheck size={17} />Decision committed. Materialization status is tracked in system health.</div>
            )}
            {decisionMutation.isError && (
              <div className="service-error compact" role="alert">
                <AlertCircle size={17} />
                <div>
                  <strong>Decision was not committed</strong>
                  <span>{errorMessage(decisionMutation.error)}</span>
                </div>
              </div>
            )}
          </section>
        )}
      </div>
    </div>
  );
}

function ScenariosView({
  scenarios,
  reopenedScenario,
  onCreate,
  onReopen,
  onCompare,
}: {
  scenarios: Scenario[];
  reopenedScenario: Scenario | null;
  onCreate: () => void;
  onReopen: (scenario: Scenario) => void;
  onCompare: (scenario: Scenario) => void;
}) {
  const selected = reopenedScenario ?? scenarios[0];
  const exportJson = (scenario: Scenario) =>
    downloadFile(`${scenario.name.replaceAll(" ", "-")}.json`, JSON.stringify(scenario, null, 2), "application/json");
  const exportCsv = (scenario: Scenario) => {
    const rows = [
      ["scenario_id", "name", "capability_id", "geography", "radius_km", "source_bundle", "policy_version", "trace_id"],
      [scenario.id, scenario.name, scenario.capabilityId, scenario.geography, String(scenario.radiusKm), scenario.sourceBundleId, scenario.policyVersion, scenario.traceId],
    ];
    downloadFile(
      `${scenario.name.replaceAll(" ", "-")}.csv`,
      rows.map((row) => row.map(csvCell).join(",")).join("\n"),
      "text/csv",
    );
  };

  return (
    <div className="desk-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">Reproducible decisions</span>
          <h1>Scenarios</h1>
          <p>Save assumptions and evidence snapshots, reopen the original result, and compare it with current data.</p>
        </div>
        <button className="primary-button" type="button" onClick={onCreate}><Plus size={16} />New scenario</button>
      </div>
      <div className="scenario-layout">
        <section className="scenario-list">
          {scenarios.map((scenario) => (
            <article key={scenario.id} className={selected?.id === scenario.id ? "scenario-row is-selected" : "scenario-row"}>
              <button type="button" className="scenario-select" onClick={() => onCompare(scenario)}>
                <span><Layers3 size={17} /></span>
                <span>
                  <strong>{scenario.name}</strong>
                  <small>{scenario.geography} · {scenario.radiusKm} km · v{scenario.version}</small>
                </span>
              </button>
              <button className="icon-button" type="button" title="Reopen scenario" aria-label={`Reopen ${scenario.name}`} onClick={() => onReopen(scenario)}>
                <RefreshCw size={16} />
              </button>
            </article>
          ))}
        </section>
        {selected && (
          <section className="scenario-detail">
            <div className="panel-heading">
              <div>
                <span className="eyebrow">Saved snapshot</span>
                <h2>{selected.name}</h2>
                <p>Updated {new Date(selected.updatedAt).toLocaleString()}</p>
              </div>
              <div className="inline-actions">
                <button className="icon-button" type="button" title="Export JSON" aria-label="Export JSON" onClick={() => exportJson(selected)}><FileJson size={18} /></button>
                <button className="icon-button" type="button" title="Export CSV" aria-label="Export CSV" onClick={() => exportCsv(selected)}><Download size={18} /></button>
              </div>
            </div>
            <div className="scenario-facts">
              <div><span>Capability</span><strong>{selected.capabilityId.replaceAll("_", " ")}</strong></div>
              <div><span>Geography</span><strong>{selected.geography}</strong></div>
              <div><span>Evidence snapshot</span><strong>{selected.evidenceSnapshotId}</strong></div>
              <div><span>Policy version</span><strong>{selected.policyVersion}</strong></div>
            </div>
            <section className="compare-section">
              <div className="section-heading compact">
                <div>
                  <span className="eyebrow">Current vs saved</span>
                  <h3>Change summary</h3>
                </div>
                <FileDiff size={18} />
              </div>
              {selected.changeSummary.length ? selected.changeSummary.map((change) => (
                <div className="change-row" key={change.field}>
                  <strong>{change.field}</strong>
                  <span>{change.prior}</span>
                  <span className="change-arrow">→</span>
                  <span>{change.current}</span>
                  <small>{change.reason}</small>
                </div>
              )) : (
                <div className="empty-state"><Check size={18} />No material changes since this snapshot.</div>
              )}
            </section>
            <section className="notes-section">
              <h3>Decision notes</h3>
              <p>{selected.notes || "No notes recorded."}</p>
            </section>
            <div className="trace-line"><Activity size={14} />Trace <code>{selected.traceId}</code></div>
          </section>
        )}
      </div>
    </div>
  );
}

function HealthPanel({
  health,
  onClose,
}: {
  health?: Awaited<ReturnType<typeof apiClient.getHealth>>;
  onClose: () => void;
}) {
  return (
    <aside className="health-panel" aria-label="System health">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">Runtime state</span>
          <h2>{health?.state === "healthy" ? "Systems healthy" : "Degraded mode active"}</h2>
        </div>
        <button className="icon-button" type="button" aria-label="Close health panel" onClick={onClose}><X size={17} /></button>
      </div>
      <p>Deterministic planning remains available. Optional live verification is cached-only.</p>
      <div className="health-list">
        {health?.components.map((component) => (
          <div key={component.name}>
            <i className={`health-dot health-${component.state}`} />
            <span><strong>{component.name}</strong><small>{component.detail}</small></span>
          </div>
        ))}
      </div>
      <dl className="compact-list">
        <div><dt>Dataset snapshot</dt><dd>{health?.snapshotVersion}</dd></div>
        <div><dt>Health trace</dt><dd><code>{health?.traceId}</code></dd></div>
      </dl>
    </aside>
  );
}
