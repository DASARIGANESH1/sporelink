from dataclasses import dataclass



@dataclass
class AnomalyResult:
    status: str
    risk_score: int
    reasons: list[str]


def detect_anomaly(
    temperature: float,
    humidity: float,
    co2: float,
    substrate_moisture: float,
) -> AnomalyResult:

    score = 0
    reasons = []

    # Temperature
    if temperature > 35:
        score += 30
        reasons.append("Temperature is unusually high")
    elif temperature < 10:
        score += 20
        reasons.append("Temperature is unusually low")

    # Humidity
    if humidity > 90:
        score += 20
        reasons.append("Humidity is unusually high")
    elif humidity < 30:
        score += 20
        reasons.append("Humidity is unusually low")

    # CO2
    if co2 > 2000:
        score += 30
        reasons.append("CO2 level is unusually high")

    # Substrate moisture
    if substrate_moisture < 20:
        score += 20
        reasons.append("Substrate moisture is unusually low")
    elif substrate_moisture > 90:
        score += 15
        reasons.append("Substrate moisture is unusually high")

    # Limit score to 100
    score = min(score, 100)

    if score >= 60:
        status = "ANOMALY"
    elif score >= 30:
        status = "WARNING"
    else:
        status = "NORMAL"

    if not reasons:
        reasons.append(
            "Telemetry values are within the expected operating range"
        )

    return AnomalyResult(
        status=status,
        risk_score=score,
        reasons=reasons,
    )