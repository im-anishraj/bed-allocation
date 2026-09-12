import json

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, no_update
from dash.dependencies import Input, Output, State

from .. import api
from ..app import app

# ------------- Components -------------


generate_patient_button = dbc.Button(
    "NEXT PATIENT",
    id="generate_patient",
    style={"width": "260px"},
)


patient_list_button = dbc.Button(
    "SEE PATIENT LIST",
    id="see_patient_list",
    style={"width": "260px"},
    color="secondary",
    outline=True,
)

patient_list_modal = dbc.Modal(
    [
        dbc.ModalHeader(
            dbc.ModalTitle(
                "🏥 Patient Admission Triage List (100 Patients — 3 General → 1 Monitor → 2 General → 1 Critical)"
            )
        ),
        dbc.ModalBody(id="patient_list_modal_body"),
        dbc.ModalFooter(
            [
                dbc.Button(
                    "RE-GENERATE 100 LIST",
                    id="refresh_patient_list",
                    color="primary",
                    size="sm",
                    className="me-2",
                ),
                dbc.Button(
                    "CLOSE",
                    id="close_patient_list",
                    color="secondary",
                    size="sm",
                ),
            ]
        ),
    ],
    id="patient_list_modal",
    size="xl",
    scrollable=True,
    is_open=False,
)

patient_details_block = dbc.Card(
    [
        dbc.Col(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            [generate_patient_button],
                            width="auto",
                        ),
                        dbc.Col(
                            [patient_list_button],
                            width="auto",
                        ),
                        dcc.Store(id="patient_details_data"),
                    ],
                    className="p-2",
                    justify="between",
                ),
                html.Div(
                    "Press the Next Patient button to generate a new random"
                    + " patient to allocate.",
                    style={"padding": 10},
                ),
                dbc.Row(
                    [
                        dbc.Col(id="patient_details"),
                    ],
                    className="p-2",
                    justify="end",
                ),
                patient_list_modal,
            ],
            className="p-4",
        )
    ],
    style={"minHeight": 550, "height": "auto"},
)


# ------------- Display -------------


def print_patient_details(patient_details):
    """
    Prints the patient details in two columns,
    with number of items in first column set by 'max_items'
    """
    max_items = 7
    return [
        dbc.Col(
            [
                dbc.Row(
                    [dbc.Col(key), dbc.Col(value, style=colour_text(value))]
                )
                for i, (key, value) in enumerate(patient_details.items())
                if i <= max_items
            ]
        ),
        dbc.Col(
            [
                dbc.Row(
                    [dbc.Col(key), dbc.Col(value, style=colour_text(value))]
                )
                for i, (key, value) in enumerate(patient_details.items())
                if i > max_items
            ]
        ),
    ]


def colour_text(input_text):
    if input_text == "Yes" or input_text == "Red":
        return {"color": "red"}
    elif input_text == "Green":
        return {"color": "green"}
    elif input_text == "Amber":
        return {"color": "orange"}


# ------------- Callbacks -------------


@app.callback(
    Output("patient_details_data", "data"),
    [
        Input("generate_patient", "n_clicks"),
    ],
)
def generate_patient_block(n_clicks):
    """
    Generates the patient details and then stores
    """
    patient_details, _ = api.get_patient()
    return json.dumps(patient_details)


@app.callback(
    Output("patient_details", "children"),
    [
        Input("patient_details_data", "data"),
    ],
)
def generate_patient_details_table(patient_details):
    """
    Creates the block containing the patient details with a prominent priority scoring banner
    """
    if not patient_details:
        return None

    patient_details = json.loads(patient_details)
    assesment_unit = api.map_assesment_unit(patient_details)
    patient_name = patient_details.pop("Name", "Patient")

    # Extract Priority attributes
    priority_score = patient_details.pop("Priority Score", "0 / 100")
    priority_level = patient_details.pop("Priority Level", "STANDARD PRIORITY")
    target_ward = patient_details.pop("Target Ward", "General")
    sequence_step = patient_details.pop("Sequence Step", None)
    contributing_factors = patient_details.pop(
        "Contributing Factors", "Routine Clinical Admission (No acute flags)"
    )

    # Configure styling based on priority level and target ward (General, Monitor, Critical)
    if "HIGH" in str(priority_level).upper() or target_ward == "Critical":
        priority_title = "HIGH PRIORITY (Immediate Bed Required)"
        badge_style = {
            "backgroundColor": "#dc3545",
            "color": "white",
            "fontSize": "0.95rem",
            "padding": "6px 12px",
            "borderRadius": "5px",
        }
        ward_badge_style = {
            "backgroundColor": "#721c24",
            "color": "white",
            "fontSize": "0.95rem",
            "fontWeight": "bold",
            "padding": "6px 14px",
            "borderRadius": "5px",
            "marginLeft": "10px",
        }
        bg_color = "#fff5f5"
        border_color = "#dc3545"
        score_color = "#dc3545"
        icon = "🚨"
    elif "MEDIUM" in str(priority_level).upper() or target_ward == "Monitor":
        priority_title = "MEDIUM PRIORITY (Urgent Admission)"
        badge_style = {
            "backgroundColor": "#fd7e14",
            "color": "white",
            "fontSize": "0.95rem",
            "padding": "6px 12px",
            "borderRadius": "5px",
        }
        ward_badge_style = {
            "backgroundColor": "#d9480f",
            "color": "white",
            "fontSize": "0.95rem",
            "fontWeight": "bold",
            "padding": "6px 14px",
            "borderRadius": "5px",
            "marginLeft": "10px",
        }
        bg_color = "#fff9f0"
        border_color = "#fd7e14"
        score_color = "#d9480f"
        icon = "⚠️"
    else:
        priority_title = "STANDARD PRIORITY (Routine Admission)"
        badge_style = {
            "backgroundColor": "#28a745",
            "color": "white",
            "fontSize": "0.95rem",
            "padding": "6px 12px",
            "borderRadius": "5px",
        }
        ward_badge_style = {
            "backgroundColor": "#155724",
            "color": "white",
            "fontSize": "0.95rem",
            "fontWeight": "bold",
            "padding": "6px 14px",
            "borderRadius": "5px",
            "marginLeft": "10px",
        }
        bg_color = "#f4fbf6"
        border_color = "#28a745"
        score_color = "#28a745"
        icon = "✅"

    # Split contributing factors into individual badge chips
    if isinstance(contributing_factors, str):
        factors_list = [f.strip() for f in contributing_factors.split(",") if f.strip()]
    else:
        factors_list = list(contributing_factors)

    factor_badges = [
        dbc.Badge(
            factor,
            color="light",
            className="border text-dark",
            style={
                "fontSize": "0.82rem",
                "fontWeight": "500",
                "padding": "4px 8px",
                "backgroundColor": "#ffffff",
                "marginRight": "6px",
                "marginBottom": "4px",
            },
        )
        for factor in factors_list
    ]

    priority_card = dbc.Card(
        [
            dbc.CardBody(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.Div(
                                        [
                                            html.Span(
                                                icon,
                                                style={
                                                    "fontSize": "1.3rem",
                                                    "marginRight": "8px",
                                                },
                                            ),
                                            dbc.Badge(
                                                priority_title,
                                                style=badge_style,
                                                className="shadow-sm",
                                            ),
                                            dbc.Badge(
                                                f"TARGET WARD: {target_ward.upper()}",
                                                style=ward_badge_style,
                                                className="shadow-sm",
                                            ),
                                            (
                                                dbc.Badge(
                                                    f"SEQUENCE: {sequence_step}",
                                                    style={
                                                        "backgroundColor": "#343a40",
                                                        "color": "white",
                                                        "fontSize": "0.85rem",
                                                        "fontWeight": "600",
                                                        "padding": "6px 12px",
                                                        "borderRadius": "5px",
                                                        "marginLeft": "10px",
                                                    },
                                                    className="shadow-sm",
                                                )
                                                if sequence_step
                                                else html.Span()
                                            ),
                                        ],
                                        className="d-flex align-items-center mb-2 flex-wrap",
                                    ),
                                    html.Div(
                                        [
                                            html.Strong(
                                                "Contributing Factors: ",
                                                style={
                                                    "fontSize": "0.85rem",
                                                    "color": "#495057",
                                                    "marginRight": "6px",
                                                },
                                            ),
                                            html.Div(
                                                factor_badges,
                                                style={
                                                    "display": "inline-flex",
                                                    "flexWrap": "wrap",
                                                    "marginTop": "4px",
                                                },
                                            ),
                                        ]
                                    ),
                                ],
                                md=8,
                            ),
                            dbc.Col(
                                [
                                    html.Div(
                                        [
                                            html.Div(
                                                "ASSIGNED WARD",
                                                style={
                                                    "fontSize": "0.75rem",
                                                    "letterSpacing": "1px",
                                                    "fontWeight": "bold",
                                                    "color": "#6c757d",
                                                },
                                            ),
                                            html.Div(
                                                f"{target_ward} Ward",
                                                style={
                                                    "fontSize": "1.35rem",
                                                    "fontWeight": "800",
                                                    "color": score_color,
                                                    "lineHeight": "1.2",
                                                    "marginBottom": "4px",
                                                },
                                            ),
                                            html.Div(
                                                "PRIORITY SCORE",
                                                style={
                                                    "fontSize": "0.75rem",
                                                    "letterSpacing": "1px",
                                                    "fontWeight": "bold",
                                                    "color": "#6c757d",
                                                },
                                            ),
                                            html.Div(
                                                priority_score,
                                                style={
                                                    "fontSize": "1.75rem",
                                                    "fontWeight": "800",
                                                    "color": score_color,
                                                    "lineHeight": "1.1",
                                                },
                                            ),
                                        ],
                                        style={"textAlign": "right"},
                                    )
                                ],
                                md=4,
                                className="d-flex align-items-center justify-content-end",
                            ),
                        ],
                        align="center",
                    )
                ],
                className="p-3",
            )
        ],
        style={
            "backgroundColor": bg_color,
            "border": f"1px solid {border_color}",
            "borderLeft": f"6px solid {border_color}",
            "borderRadius": "8px",
            "marginBottom": "16px",
            "width": "100%",
        },
    )

    details_block = dbc.Col(
        [
            dbc.Row(
                html.H5(
                    f"{patient_name} from {assesment_unit}",
                    className="mb-2",
                )
            ),
            dbc.Row(priority_card),
            dbc.Row(print_patient_details(patient_details)),
        ]
    )
    return details_block


# ------------- 100 Patient List Modal & Rendering -------------


def render_patient_list_table(patients=None):
    if patients is None:
        patients = api.generate_100_patients()

    from collections import Counter
    counts = Counter(p.get("Target Ward", "General") for p in patients)

    pattern_banner = dbc.Alert(
        [
            html.Strong("🔄 Generation Sequence Loop: "),
            html.Span("3 General → 1 Monitor → 2 General → 1 Critical (Repeated cyclically across all 100 admissions)"),
        ],
        color="info",
        className="py-2 px-3 mb-2 border shadow-sm",
        style={"fontSize": "0.9rem"},
    )

    summary_bar = dbc.Row(
        [
            dbc.Col(
                dbc.Alert(
                    [
                        html.Div(
                            "TOTAL COHORT",
                            style={"fontSize": "0.75rem", "fontWeight": "bold"},
                        ),
                        html.H4(str(len(patients)), className="mb-0 text-dark"),
                    ],
                    color="light",
                    className="text-center py-2 border mb-0",
                ),
                width=3,
            ),
            dbc.Col(
                dbc.Alert(
                    [
                        html.Div(
                            "🚨 CRITICAL WARD",
                            style={"fontSize": "0.75rem", "fontWeight": "bold"},
                        ),
                        html.H4(
                            str(counts.get("Critical", 0)),
                            className="mb-0 text-danger",
                        ),
                    ],
                    color="danger",
                    className="text-center py-2 border mb-0",
                ),
                width=3,
            ),
            dbc.Col(
                dbc.Alert(
                    [
                        html.Div(
                            "⚠️ MONITOR WARD",
                            style={"fontSize": "0.75rem", "fontWeight": "bold"},
                        ),
                        html.H4(
                            str(counts.get("Monitor", 0)),
                            className="mb-0 text-warning",
                        ),
                    ],
                    color="warning",
                    className="text-center py-2 border mb-0",
                ),
                width=3,
            ),
            dbc.Col(
                dbc.Alert(
                    [
                        html.Div(
                            "✅ GENERAL WARD",
                            style={"fontSize": "0.75rem", "fontWeight": "bold"},
                        ),
                        html.H4(
                            str(counts.get("General", 0)),
                            className="mb-0 text-success",
                        ),
                    ],
                    color="success",
                    className="text-center py-2 border mb-0",
                ),
                width=3,
            ),
        ],
        className="mb-3 g-2",
    )

    table_rows = []
    for idx, p in enumerate(patients):
        ward = p.get("Target Ward", "General")
        order_no = p.get("Order #", idx + 1)
        pattern_step = p.get("Pattern Step", f"Step {(idx % 7) + 1}/7 ({ward})")
        if ward == "Critical":
            badge_color = "danger"
        elif ward == "Monitor":
            badge_color = "warning"
        else:
            badge_color = "success"

        table_rows.append(
            html.Tr(
                [
                    html.Td(str(order_no), style={"fontWeight": "bold", "textAlign": "center", "width": "45px"}),
                    html.Td(p.get("Patient ID", "-"), style={"fontWeight": "600"}),
                    html.Td(
                        dbc.Badge(
                            pattern_step,
                            color="dark",
                            style={"fontSize": "0.78rem", "padding": "4px 8px"},
                        )
                    ),
                    html.Td(p.get("Name", "-")),
                    html.Td(f"{p.get('Age', '-')}y / {str(p.get('Sex', '-')).capitalize()}"),
                    html.Td(
                        f"{str(p.get('Division', '-')).capitalize()} ({str(p.get('Specialty', '-')).replace('_', ' ').capitalize()})"
                    ),
                    html.Td(
                        html.Strong(p.get("Priority Score", "0 / 100")),
                        style={"textAlign": "center"},
                    ),
                    html.Td(
                        dbc.Badge(
                            ward.upper(),
                            color=badge_color,
                            style={"padding": "5px 10px", "fontSize": "0.82rem"},
                        ),
                        style={"textAlign": "center"},
                    ),
                    html.Td(
                        p.get("Contributing Factors", "-"),
                        style={"fontSize": "0.83rem", "maxWidth": "350px"},
                    ),
                ]
            )
        )

    table = dbc.Table(
        [
            html.Thead(
                html.Tr(
                    [
                        html.Th("#", style={"textAlign": "center"}),
                        html.Th("Patient ID"),
                        html.Th("Cycle Step"),
                        html.Th("Name"),
                        html.Th("Age / Sex"),
                        html.Th("Division / Specialty"),
                        html.Th("Score", style={"textAlign": "center"}),
                        html.Th("Target Ward", style={"textAlign": "center"}),
                        html.Th("Contributing Clinical Factors"),
                    ]
                )
            ),
            html.Tbody(table_rows),
        ],
        bordered=True,
        hover=True,
        responsive=True,
        striped=True,
        size="sm",
        style={"fontSize": "0.88rem"},
    )

    return html.Div(
        [
            pattern_banner,
            summary_bar,
            html.Div(
                table,
                style={
                    "maxHeight": "520px",
                    "overflowY": "auto",
                    "border": "1px solid #dee2e6",
                    "borderRadius": "4px",
                },
            ),
        ]
    )


@app.callback(
    [
        Output("patient_list_modal", "is_open"),
        Output("patient_list_modal_body", "children"),
    ],
    [
        Input("see_patient_list", "n_clicks"),
        Input("close_patient_list", "n_clicks"),
        Input("refresh_patient_list", "n_clicks"),
    ],
    [State("patient_list_modal", "is_open")],
    prevent_initial_call=True,
)
def toggle_patient_list_modal(n_open, n_close, n_refresh, is_open):
    ctx = dash.callback_context
    if not ctx.triggered:
        return False, no_update

    button_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if button_id == "close_patient_list":
        return False, no_update

    if button_id in ("see_patient_list", "refresh_patient_list"):
        content = render_patient_list_table()
        return True, content

    return is_open, no_update
