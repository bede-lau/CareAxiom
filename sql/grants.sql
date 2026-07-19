-- Replace service-principal placeholders with their applicationId UUID values.
-- Grant only project-owned objects.
GRANT USE CATALOG ON CATALOG {{project_catalog}} TO `{{app_service_principal}}`;
GRANT USE SCHEMA ON SCHEMA {{project_catalog}}.bronze TO `{{app_service_principal}}`;
GRANT SELECT ON TABLE {{project_catalog}}.bronze.facility_source_snapshot TO `{{app_service_principal}}`;
GRANT USE SCHEMA ON SCHEMA {{project_catalog}}.gold TO `{{app_service_principal}}`;
GRANT SELECT ON SCHEMA {{project_catalog}}.gold TO `{{app_service_principal}}`;
GRANT MODIFY ON TABLE {{project_catalog}}.gold.facility_review_overlay TO `{{app_service_principal}}`;
GRANT MODIFY ON TABLE {{project_catalog}}.gold.operational_event_materialization TO `{{app_service_principal}}`;
GRANT USE SCHEMA ON SCHEMA {{project_catalog}}.silver TO `{{app_service_principal}}`;
GRANT SELECT ON SCHEMA {{project_catalog}}.silver TO `{{app_service_principal}}`;

GRANT USE CATALOG ON CATALOG {{project_catalog}} TO `{{pipeline_service_principal}}`;
GRANT USE SCHEMA ON SCHEMA {{project_catalog}}.bronze TO `{{pipeline_service_principal}}`;
GRANT USE SCHEMA ON SCHEMA {{project_catalog}}.silver TO `{{pipeline_service_principal}}`;
GRANT USE SCHEMA ON SCHEMA {{project_catalog}}.gold TO `{{pipeline_service_principal}}`;
GRANT USE SCHEMA ON SCHEMA {{project_catalog}}.evaluation TO `{{pipeline_service_principal}}`;
GRANT SELECT, MODIFY, CREATE TABLE ON SCHEMA {{project_catalog}}.bronze TO `{{pipeline_service_principal}}`;
GRANT SELECT, MODIFY, CREATE TABLE ON SCHEMA {{project_catalog}}.silver TO `{{pipeline_service_principal}}`;
GRANT SELECT, MODIFY, CREATE TABLE ON SCHEMA {{project_catalog}}.gold TO `{{pipeline_service_principal}}`;
GRANT SELECT, MODIFY, CREATE TABLE ON SCHEMA {{project_catalog}}.evaluation TO `{{pipeline_service_principal}}`;

-- Source access remains read-only and must be granted by the source owner.
-- No MODIFY, CREATE, or ownership grant is issued against {{source_catalog}}.
GRANT USE CATALOG ON CATALOG {{source_catalog}} TO `{{pipeline_service_principal}}`;
GRANT USE SCHEMA ON SCHEMA {{source_catalog}}.{{source_schema}} TO `{{pipeline_service_principal}}`;
GRANT SELECT ON TABLE {{source_catalog}}.{{source_schema}}.facilities TO `{{pipeline_service_principal}}`;
GRANT SELECT ON TABLE {{source_catalog}}.{{source_schema}}.india_post_pincode_directory TO `{{pipeline_service_principal}}`;
GRANT SELECT ON TABLE {{source_catalog}}.{{source_schema}}.nfhs_5_district_health_indicators TO `{{pipeline_service_principal}}`;
