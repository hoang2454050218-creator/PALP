# PALP Test Traceability Matrix

> Maps every test case ID in QA_STANDARD.md to its implementation file and test function.
> Use this to verify coverage completeness before release.

## accounts (AUTH + RBAC + CONSENT)

| ID | Description | File | Test class/function |
|----|-------------|------|---------------------|
| AUTH-001 | Login success | `accounts/tests/test_auth_api.py` | `TestLogin::test_login_success` |
| AUTH-002 | Login fail wrong password | `accounts/tests/test_auth_api.py` | `TestLogin::test_wrong_password` |
| AUTH-003 | Login fail unknown user | `accounts/tests/test_auth_api.py` | `TestLogin::test_unknown_user` |
| AUTH-004 | No token -> 401 | `accounts/tests/test_auth_api.py` | `TestProtectedEndpoint::test_no_token` |
| AUTH-005 | Expired token -> 401 | `accounts/tests/test_auth_api.py` | `TestProtectedEndpoint::test_expired_token` |
| AUTH-006 | Refresh token success | `accounts/tests/test_auth_api.py` | `TestTokenRefresh::test_refresh` |
| AUTH-007 | Revoked refresh -> 401 | `accounts/tests/test_auth_api.py` | `TestTokenRefresh::test_revoked` |
| AUTH-008 | Register new user | `accounts/tests/test_auth_api.py` | `TestRegister::test_register_success` |
| AUTH-009 | Register duplicate -> 400 | `accounts/tests/test_auth_api.py` | `TestRegister::test_duplicate_username` |
| RBAC-001..007 | RBAC matrix 23 combos | `tests/security/test_authz_matrix.py` | `TestRBACMatrix` |
| CONSENT-001 | No consent -> no collection | `privacy/tests.py` | `TestConsentGate` |
| CONSENT-002 | Consent saves correctly | `privacy/tests.py` | `TestConsentRecord` |
| CONSENT-003 | Withdraw consent | `privacy/tests.py` | `TestConsentWithdrawal` |

## assessment (ASSESS)

| ID | Description | File | Test class/function |
|----|-------------|------|---------------------|
| ASSESS-001 | Start creates session | `assessment/tests/test_assessment_api.py` | `TestStartAssessment` |
| ASSESS-002 | Submit answer saved | `assessment/tests/test_assessment_api.py` | `TestSubmitAnswer` |
| ASSESS-003 | Complete scores correctly | `assessment/tests/test_services.py` | `TestScoring` |
| ASSESS-004 | LearnerProfile created | `assessment/tests/test_services.py` | `TestLearnerProfile` |
| ASSESS-005 | initial_mastery mapping | `assessment/tests/test_services.py` | `TestInitialMastery` |
| ASSESS-006 | Save progress | `assessment/tests/test_assessment_api.py` | `TestSaveProgress` |
| ASSESS-007 | No duplicate sessions | `tests/integration/test_product_correctness.py` | `TestAP04NoDoubleCount::test_no_duplicate_active_sessions` |
| ASSESS-008..012 | Edge cases | `assessment/tests/test_assessment_matrix.py` | various |

## adaptive (BKT + PATH + CACHE + RETRY + SUBMIT)

| ID | Description | File | Test class/function |
|----|-------------|------|---------------------|
| BKT-001 | P(L\|correct) formula | `adaptive/tests/test_bkt_engine.py` | `TestBKTCorrect` |
| BKT-002 | P(L\|wrong) formula | `adaptive/tests/test_bkt_engine.py` | `TestBKTWrong` |
| BKT-003 | P(L_new) update | `adaptive/tests/test_bkt_engine.py` | `TestBKTTransition` |
| BKT-004 | Golden vector: 5 correct | `adaptive/tests/test_bkt_engine.py` | `TestGoldenVector::test_5_correct_monotonic` |
| BKT-005 | Golden vector: 5 wrong | `adaptive/tests/test_bkt_engine.py` | `TestGoldenVector::test_5_wrong_no_increase` |
| BKT-006 | Golden vector: [D,D,S,D,D] | `adaptive/tests/test_bkt_engine.py` | `TestGoldenVector::test_mixed_pattern` |
| BKT-007 | Params in [0,1] | `adaptive/tests/test_bkt_engine.py` + `adaptive/tests/test_bkt_property.py` | bounds checks |
| BKT-008 | No NaN/Infinity | `adaptive/tests/test_bkt_property.py` | `TestBKTBounds` |
| PATH-001 | P<0.60 -> supplement | `adaptive/tests/test_pathway_api.py` | `TestPathwayDecision::test_low_mastery` |
| PATH-002 | 0.60-0.85 -> continue | `adaptive/tests/test_pathway_api.py` | `TestPathwayDecision::test_mid_mastery` |
| PATH-003 | P>0.85 -> advance | `adaptive/tests/test_pathway_api.py` | `TestPathwayDecision::test_high_mastery` |
| PATH-004 | Decision consistency | `adaptive/tests/test_pathway_api.py` | `TestPathwayDecision::test_consistency` |
| SUBMIT-001..003 | Submit task | `adaptive/tests/test_adaptive_matrix.py` | `TestSubmitTask` |
| RETRY-001..003 | Retry flow | `adaptive/tests/test_adaptive_matrix.py` | `TestRetryFlow` |
| CACHE-001..003 | Redis cache | `adaptive/tests/test_pathway_api.py` | `TestMasteryCache` |

## dashboard (EW + ALERT + ACTION + DASH)

| ID | Description | File | Test class/function |
|----|-------------|------|---------------------|
| EW-001 | Inactive >= 5 days -> RED | `dashboard/tests/test_early_warning.py` | `TestInactivityAlert::test_six_days_inactive_triggers_red` |
| EW-002 | Inactive 3-4 days -> YELLOW | `dashboard/tests/test_early_warning.py` | `TestInactivityAlert::test_four_days_inactive_triggers_yellow` |
| EW-003 | Active -> no alert | `dashboard/tests/test_early_warning.py` | `TestInactivityAlert::test_recently_active_no_alert` |
| EW-004 | Retry fail >= 3 -> RED | `dashboard/tests/test_early_warning.py` | `TestRetryFailureAlert` |
| EW-005 | Milestone lag -> YELLOW | `dashboard/tests/test_early_warning.py` | `TestMilestoneLagAlert` |
| EW-006 | Normal -> GREEN | `tests/integration/test_product_correctness.py` | `TestAP05NoFalseAlert::test_active_student_not_flagged` |
| EW-007 | Nightly batch | `dashboard/tests/test_dashboard_matrix.py` | `TestNightlyBatch` |
| EW-008 | Alert has full fields | `tests/integration/test_product_correctness.py` | `TestAP02NoUnexplainableState::test_alert_always_has_reason` |
| EW-009 | Reason human-readable | `tests/integration/test_product_correctness.py` | `TestAP02NoUnexplainableState::test_alert_reason_is_human_readable` |
| DASH-001 | Overview counts correct | `dashboard/tests/test_early_warning.py` | `TestClassOverview::test_returns_correct_counts` |
| DASH-002 | Overview < 3s (cached) | `tests/load/slo_assertions.py` | performance test |

## events (EVT) + Event Completeness (EC)

| ID | Description | File | Test class/function |
|----|-------------|------|---------------------|
| EVT-001 | Track single event | `events/tests/test_tracking.py` | `TestTrackEvent::test_creates_event_returns_201` |
| EVT-002 | Batch track | `events/tests/test_tracking.py` | `TestBatchTrack::test_creates_multiple_events` |
| EVT-003 | 8 types fire+persist | `events/tests/test_event_completeness.py` | `TestEVT003CoreEventTypes` |
| EVT-008 | No duplicate (idempotency) | `events/tests/test_event_completeness.py` | `TestEVT008Deduplication` |
| EVT-009 | Schema validation | `events/tests/test_event_completeness.py` | `TestEVT009SchemaValidation` |
| EVT-010 | RBAC on events | `events/tests/test_event_completeness.py` | `TestEVT010EventRBAC` |
| EC-01 | session_started fields | `events/tests/test_event_completeness.py` | `TestEC01SessionStarted` |
| EC-02 | session_ended duration | `events/tests/test_event_completeness.py` | `TestEC02SessionEnded` |
| EC-03 | assessment_completed score | `events/tests/test_event_completeness.py` | `TestEC03AssessmentCompleted` |
| EC-04 | micro_task_completed task_id | `events/tests/test_event_completeness.py` | `TestEC04MicroTaskCompleted` |
| EC-05 | content_intervention concept | `events/tests/test_event_completeness.py` | `TestEC05ContentIntervention` |
| EC-06 | gv_action_taken targets | `events/tests/test_event_completeness.py` | `TestEC06GvActionTaken` |
| EC-07 | wellbeing_nudge_shown | `events/tests/test_event_completeness.py` | `TestEC07WellbeingNudgeShown` |
| EC-08 | page_view page field | `events/tests/test_event_completeness.py` | `TestEC08PageView` |

## wellbeing (WB)

| ID | Description | File | Test class/function |
|----|-------------|------|---------------------|
| WB-001 | > 50 min -> nudge | `wellbeing/tests/test_nudge.py` | `TestCheckWellbeing::test_nudge_over_limit` |
| WB-002 | < 50 min -> no nudge | `wellbeing/tests/test_nudge.py` | `TestCheckWellbeing::test_no_nudge_under_limit` |
| WB-003 | Response saved | `wellbeing/tests/test_nudge.py` | `TestNudgeResponse` |
| WB-004 | Acceptance rate trackable | `wellbeing/tests/test_nudge.py` | `TestWB004AcceptanceRateTracking` |
| WB-005 | No flow break | `wellbeing/tests/test_nudge.py` | `TestWB005NudgeNoFlowBreak` |
| WB-006 | History viewable | `wellbeing/tests/test_nudge.py` | `TestMyNudges` |

## Data Cleaning (DC)

| ID | Description | File | Test class/function |
|----|-------------|------|---------------------|
| DC-01 | Missing data detection | `tests/data_qa/test_data_cleaning.py` | `TestDC01MissingDataDetection` |
| DC-02 | Missing classification | `tests/data_qa/test_data_cleaning.py` | `TestDC02MissingClassification` |
| DC-03 | KNN imputation valid | `tests/data_qa/test_data_cleaning.py` | `TestDC03KNNImputation` |
| DC-04 | Outlier screening | `tests/data_qa/test_data_cleaning.py` | `TestDC04OutlierScreening` |
| DC-05 | Idempotency | `tests/data_qa/test_data_cleaning.py` | `TestDC05Idempotency` |
| DC-06 | Quality score >= 70% | `tests/data_qa/test_data_cleaning.py` | `TestDC06QualityScore` |

## KPI Integrity (KPIINT)

| ID | Description | File | Test class/function |
|----|-------------|------|---------------------|
| KPIINT-001 | Each KPI has owner | `analytics/tests/test_kpi_integrity.py` | `TestKPIOwnership` |
| KPIINT-002 | Traces to source events | `analytics/tests/test_kpi_integrity.py` | `TestKPITraceability` |
| KPIINT-003 | query_function importable | `analytics/tests/test_kpi_integrity.py` | `TestKPIReproducibility` |
| KPIINT-004 | Locked rejects changes | `analytics/tests/test_kpi_integrity.py` | `TestKPILocking` |
| KPIINT-005 | Periods no overlap | `analytics/tests/test_kpi_integrity.py` | `TestPeriodSeparation` |
| KPIINT-006 | Report has schema_version | `analytics/tests/test_kpi_integrity.py` | `TestDashboardVersioning` |
| KPIINT-007 | Zero events -> FAIL | `analytics/tests/test_kpi_integrity.py` | `TestZeroRawDataDetection` |
| KPIINT-008 | Definition drift detected | `analytics/tests/test_kpi_integrity.py` | `TestDefinitionDriftDetection` |
| KPIINT-009 | Event gap > 24h flagged | `analytics/tests/test_kpi_integrity.py` | `TestEventGapDetection` |
| KPIINT-010 | Tracking bug detected | `analytics/tests/test_kpi_integrity.py` | `TestTrackingBugDetection` |
| KPIINT-011 | Version snapshot created | `analytics/tests/test_kpi_integrity.py` | `TestVersioning` |
| KPIINT-012 | Lineage has sample IDs | `analytics/tests/test_kpi_integrity.py` | `TestLineageLogging` |
| KPIINT-013 | Baseline locked after lock | `analytics/tests/test_kpi_integrity.py` | `TestBaselineLocking` |

## Product Correctness Anti-patterns (AP)

| ID | Description | File | Test class/function |
|----|-------------|------|---------------------|
| AP-01 | No dead-end flow | `tests/integration/test_product_correctness.py` | `TestAP01NoDeadEnd` |
| AP-02 | No unexplainable state | `tests/integration/test_product_correctness.py` | `TestAP02NoUnexplainableState` |
| AP-03 | No lost state mid-flow | `tests/integration/test_product_correctness.py` | `TestAP03NoLostState` |
| AP-04 | No double-count | `tests/integration/test_product_correctness.py` | `TestAP04NoDoubleCount` |
| AP-05 | No false alert | `tests/integration/test_product_correctness.py` | `TestAP05NoFalseAlert` |

## API Discipline (BD-R, ARG)

| ID | Description | File | Test class/function |
|----|-------------|------|---------------------|
| BD-R01 | No 500 for validation | `tests/contract/test_api_discipline.py` | `TestBDR01NoValidation500` |
| BD-R02 | No stack trace | `tests/contract/test_api_discipline.py` | `TestBDR02NoStackTrace` |
| BD-R03 | Actionable errors | `tests/contract/test_api_discipline.py` | `TestBDR03ActionableErrors` |
| BD-R04 | Request ID on learning endpoints | `tests/contract/test_api_discipline.py` | `TestBDR04RequestId` |
| BD-R05 | Idempotent POST | `tests/contract/test_api_discipline.py` | `TestBDR05Idempotency` |
| ARG | API completeness | `tests/contract/test_api_discipline.py` | `TestAPICompleteness` |

## Module Edge Cases (AS, AD, BD, GV)

| ID | Description | File | Test class/function |
|----|-------------|------|---------------------|
| AS-04 | Timeout submit | `tests/integration/test_module_edge_cases.py` | `TestAS04TimeoutSubmit` |
| AS-06 | Retake assessment | `tests/integration/test_module_edge_cases.py` | `TestAS06Retake` |
| AS-07 | Cross-device resume | `tests/integration/test_module_edge_cases.py` | `TestAS07CrossDevice` |
| AS-08 | Token expiry mid-assessment | `tests/integration/test_module_edge_cases.py` | `TestAS08TokenExpiry` |
| AD-03 | Multi-concept flagging | `tests/integration/test_module_edge_cases.py` | `TestAD03MultiConcept` |
| AD-05 | Offline state resume | `tests/integration/test_module_edge_cases.py` | `TestAD05OfflineResume` |
| AD-07 | Retry alert creation | `tests/integration/test_module_edge_cases.py` | `TestAD07RetryAlert` |
| AD-08 | Concurrent mastery update | `tests/integration/test_module_edge_cases.py` | `TestAD08ConcurrentMastery` |
| AD-09 | Rule version stability | `tests/integration/test_module_edge_cases.py` | `TestAD09RuleVersionChange` |
| AD-10 | Intervention fallback | `tests/integration/test_module_edge_cases.py` | `TestAD10InterventionFallback` |
| BD-04 | Flexible milestone order | `tests/integration/test_module_edge_cases.py` | `TestBD04FlexOrder` |
| BD-06 | Concurrent progress | `tests/integration/test_module_edge_cases.py` | `TestBD06ConcurrentProgress` |
| BD-08 | Prerequisite enforcement | `tests/integration/test_module_edge_cases.py` | `TestBD08Prerequisites` |
| GV-04 | Legitimate absence | `tests/integration/test_module_edge_cases.py` | `TestGV04LegitimateAbsence` |
| GV-08 | Follow-up measurement | `tests/integration/test_module_edge_cases.py` | `TestGV08FollowUp` |

## Observability (OB + OD)

| ID | Description | File | Test class/function |
|----|-------------|------|---------------------|
| OB-01 | Event completeness fields | `tests/integration/test_observability.py` | `TestOB01EventCompleteness` |
| OB-02 | Event deduplication | `tests/integration/test_observability.py` | `TestOB02EventDeduplication` |
| OB-03 | Clock skew normalized | `tests/integration/test_observability.py` | `TestOB03ClockNormalization` |
| OB-04 | Zero orphan events | `tests/integration/test_observability.py` | `TestOB04NoOrphanEvents` |
| OB-05 | Critical events BE-confirmed | `tests/integration/test_observability.py` | `TestOB05CriticalEventConfirmation` |
| OD-01..09 | Operations dashboard panels | `tests/integration/test_observability.py` | `TestOperationsDashboard` |

## Privacy Hardened (PP + PRG)

| ID | Description | File | Test class/function |
|----|-------------|------|---------------------|
| PP-01 | Consent per-purpose | `tests/integration/test_privacy_hardened.py` | `TestPP01ConsentPerPurpose` |
| PP-02 | Export 4 data tiers | `tests/integration/test_privacy_hardened.py` | `TestPP02DataTiers` |
| PP-03 | Delete policy by tier | `tests/integration/test_privacy_hardened.py` | `TestPP03DeletePolicy` |
| PP-05 | Lecturer minimal access | `tests/integration/test_privacy_hardened.py` | `TestPP05LecturerMinimalAccess` |
| PRG-06 | Zero PII leak | `tests/integration/test_privacy_hardened.py` | `TestPRG06NoPIILeak` |
| PRG-07 | No tier confusion | `tests/integration/test_privacy_hardened.py` | `TestPRG07NoTierConfusion` |

## Security Hardened (SG + SK)

| ID | Description | File | Test class/function |
|----|-------------|------|---------------------|
| SG-01 | AuthN: logout clears session | `tests/security/test_security_hardened.py` | `TestSG01AuthN` |
| SG-03 | Input validation server-side | `tests/security/test_security_hardened.py` | `TestSG03InputValidation` |
| SG-04 | Zero injection (extended XSS) | `tests/security/test_security_hardened.py` | `TestSG04Injection` |
| SG-07 | No sensitive data leak | `tests/security/test_security_hardened.py` | `TestSG07SensitiveData` |
| SG-08 | Audit log completeness | `tests/security/test_security_hardened.py` | `TestSG08Audit` |
| SG-09 | Rate limiting | `tests/security/test_security_hardened.py` | `TestSG09RateLimit` |
| SK-01 | IDOR cross-class leak | `tests/security/test_security_hardened.py` | `TestSK01IDORCrossClass` |
| SK-02 | Export requires auth + ownership | `tests/security/test_security_hardened.py` | `TestSK02ExportAuth` |
| SK-03 | Token invalid after logout | `tests/security/test_security_hardened.py` | `TestSK03TokenInvalidation` |
| SK-05 | Audit log immutable | `tests/security/test_security_hardened.py` | `TestSK05AuditImmutable` |
| SK-06 | Deleted data not accessible | `tests/security/test_security_hardened.py` | `TestSK06DeletedDataGone` |

## Core Feature Criteria (F1-F5)

| ID | Description | File | Test class/function |
|----|-------------|------|---------------------|
| F1-03 | Score calculation exact | `tests/integration/test_feature_criteria.py` | `TestF1Assessment::test_f1_03_score_calculation_exact` |
| F1-06 | Two tabs -> 1 session | `tests/integration/test_feature_criteria.py` | `TestF1Assessment::test_f1_06_two_tabs_only_one_session` |
| F1-08 | Submit audit event | `tests/integration/test_feature_criteria.py` | `TestF1Assessment::test_f1_08_submit_creates_audit_event` |
| F2-02 | Intervention version info | `tests/integration/test_feature_criteria.py` | `TestF2Adaptive::test_f2_02_intervention_has_version_info` |
| F2-03 | Mastery delta recorded | `tests/integration/test_feature_criteria.py` | `TestF2Adaptive::test_f2_03_intervention_records_mastery_delta` |
| F2-04 | No repeated intervention | `tests/integration/test_feature_criteria.py` | `TestF2Adaptive::test_f2_04_no_repeated_intervention_without_gain` |
| F2-05 | No infinite retry loop | `tests/integration/test_feature_criteria.py` | `TestF2Adaptive::test_f2_05_no_infinite_retry_loop` |
| F2-06 | Pathway has message | `tests/integration/test_feature_criteria.py` | `TestF2Adaptive::test_f2_06_pathway_response_has_message` |
| F3-01 | Progress from data | `tests/integration/test_feature_criteria.py` | `TestF3BackwardDesign::test_f3_01_progress_from_data_not_ui` |
| F3-02 | Idempotent completion | `tests/integration/test_feature_criteria.py` | `TestF3BackwardDesign::test_f3_02_task_completion_idempotent` |
| F3-06 | No impossible progress | `tests/integration/test_feature_criteria.py` | `TestF3BackwardDesign::test_f3_06_no_impossible_progress` |
| F4-01 | Alert 5 required fields | `tests/integration/test_feature_criteria.py` | `TestF4Dashboard::test_f4_01_alert_has_all_5_required_fields` |
| F4-05 | Insufficient data flagged | `tests/integration/test_feature_criteria.py` | `TestF4Dashboard::test_f4_05_insufficient_data_flagged` |
| F4-06 | Lecturer scoped | `tests/integration/test_feature_criteria.py` | `TestF4Dashboard::test_f4_06_lecturer_scoped_to_own_class` |
| F5-01 | ETL run metadata | `tests/integration/test_feature_criteria.py` | `TestF5Pipeline::test_f5_01_etl_run_has_metadata` |
| F5-02 | No silent coercion | `tests/integration/test_feature_criteria.py` | `TestF5Pipeline::test_f5_02_no_silent_coercion` |
| F5-05 | Reproducible pipeline | `tests/integration/test_feature_criteria.py` | `TestF5Pipeline::test_f5_05_pipeline_reproducible` |
| F5-06 | Atomic failure | `tests/integration/test_feature_criteria.py` | `TestF5Pipeline::test_f5_06_atomic_failure_no_partial_output` |

## Learning Integrity (LI-F)

| ID | Description | File | Test class/function |
|----|-------------|------|---------------------|
| LI-F01 | Wrong concept supplementary | `tests/integration/test_learning_integrity.py` | `TestLIF01WrongConceptIntervention` |
| LI-F02 | Premature difficulty increase | `tests/integration/test_learning_integrity.py` | `TestLIF02PrematureDifficultyIncrease` |
| LI-F03 | Mass false flagging | `tests/integration/test_learning_integrity.py` | `TestLIF03MassFalseFlagging` |
| LI-F04 | No return to main flow | `tests/integration/test_learning_integrity.py` | `TestLIF04NoReturnToMainFlow` |
| LI-F05 | Inflated progress | `tests/integration/test_learning_integrity.py` | `TestLIF05InflatedProgress` |
| LI-F06 | Alert without reason | `tests/integration/test_learning_integrity.py` | `TestLIF06AlertWithoutReason` |
| LI-Safety | Psychological safety in labels | `tests/integration/test_learning_integrity.py` | `TestLIPsychologicalSafety` |

## E2E Journeys

| ID | Description | File |
|----|-------------|------|
| J1 | Student Onboarding | `e2e/journeys/journey-a-new-student.spec.ts` |
| J2 | Student Learning Loop | `e2e/journeys/journey-b-adaptive.spec.ts` |
| J3 | Student Retry Flow | `e2e/journeys/journey-b-adaptive.spec.ts` |
| J4 | Lecturer Early Warning | `e2e/journeys/journey-c-lecturer.spec.ts` |
| J5 | Lecturer Intervention | `e2e/journeys/journey-c-lecturer.spec.ts` |
| J6 | Wellbeing Nudge | `e2e/journeys/journey-e-wellbeing.spec.ts` |
| J7 | Data Pipeline | `e2e/journeys/journey-f-data-pipeline.spec.ts` |
| Privacy | Privacy Request | `e2e/journeys/journey-d-privacy.spec.ts` |

## Frontend (FE) — E2E specs

| ID | Description | File |
|----|-------------|------|
| FE-001 | Login render + submit | `e2e/auth-flow.spec.ts` |
| FE-002 | Login error message | `e2e/auth-flow.spec.ts` |
| FE-003 | Student dashboard | `e2e/journeys/journey-a-new-student.spec.ts` (A8) |
| FE-004 | Assessment UI | `e2e/student-assessment.spec.ts` |
| FE-005 | Pathway page | `e2e/student-pathway.spec.ts` |
| FE-007 | Lecturer overview | `e2e/lecturer-dashboard.spec.ts` |
| FE-008 | Lecturer alerts | `e2e/lecturer-dashboard.spec.ts` |
| FE-010 | Wellbeing nudge | `e2e/student-wellbeing.spec.ts` + `e2e/journeys/journey-e-wellbeing.spec.ts` |
| FE-017 | Quiz radiogroup a11y | `e2e/accessibility.spec.ts` |
| FE-019 | Skip link | `e2e/accessibility.spec.ts` |
| FE-022 | Contrast WCAG AA | `e2e/accessibility.spec.ts` |
| FE-024 | axe-core scan | `e2e/accessibility.spec.ts` |

---

> **Note**: Test IDs that map to multiple test functions indicate comprehensive coverage. If a test ID does not appear here, verify it is covered by an existing test or add it.
