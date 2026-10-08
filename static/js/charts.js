/**
 * SYSTÈME NUMÉRIQUE DE GESTION PÉNITENTIAIRE (SGP) - PRISON CENTRALE DE MAKALA
 * Configuration des Graphiques Chart.js (Dashboard & Analytics)
 */

document.addEventListener('DOMContentLoaded', function () {
    // 1. Graphique par Statut Judiciaire (Doughnut Chart)
    const ctxStatut = document.getElementById('chartStatutJudiciaire');
    if (ctxStatut && typeof window.statsStatutData !== 'undefined') {
        new Chart(ctxStatut, {
            type: 'doughnut',
            data: {
                labels: window.statsStatutData.labels,
                datasets: [{
                    data: window.statsStatutData.values,
                    backgroundColor: [
                        '#EAB308', // Prévenu (Jaune)
                        '#DC2626', // Condamné (Rouge)
                        '#0284C7', // Transféré (Bleu)
                        '#16A34A', // Libéré (Vert)
                        '#1E293B'  // Décédé (Noir)
                    ],
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            font: { family: 'Inter', size: 12 },
                            padding: 15
                        }
                    }
                },
                cutout: '70%'
            }
        });
    }

    // 2. Graphique par Niveau de Dangerosité (Bar Chart)
    const ctxDanger = document.getElementById('chartDangerosite');
    if (ctxDanger && typeof window.statsDangerData !== 'undefined') {
        new Chart(ctxDanger, {
            type: 'bar',
            data: {
                labels: window.statsDangerData.labels,
                datasets: [{
                    label: 'Nombre de Détenus',
                    data: window.statsDangerData.values,
                    backgroundColor: [
                        'rgba(22, 163, 74, 0.85)',  // Faible
                        'rgba(2, 132, 199, 0.85)',   // Moyen
                        'rgba(234, 179, 8, 0.85)',   // Élevé
                        'rgba(220, 38, 38, 0.85)'    // Critique
                    ],
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { stepSize: 1 }
                    }
                }
            }
        });
    }
});
