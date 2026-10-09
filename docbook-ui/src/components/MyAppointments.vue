<template>
	<div class="appointments-page">

		<!-- Background decoration -->
		<div class="bg-orb orb-blue"></div>
		<div class="bg-orb orb-teal"></div>

		<div class="page-container">

			<!-- Header -->
			<section class="page-header">
				<div>
					<div class="eyebrow">
						<span class="eyebrow-dot"></span>
						YOUR HEALTHCARE
					</div>

					<h1>My Appointments</h1>

					<p>
						Manage your upcoming and previous doctor appointments
						in one place.
					</p>
				</div>

				<div class="header-icon">
					<svg
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="1.8"
					>
						<rect x="3" y="4" width="18" height="17" rx="3" />
						<path d="M16 2v4M8 2v4M3 10h18" />
						<path d="M8 14h.01M12 14h.01M16 14h.01" />
					</svg>
				</div>
			</section>


			<!-- Loading -->
			<div v-if="loading" class="state-card">
				<div class="loader"></div>
				<h3>Loading appointments...</h3>
				<p>Please wait while we fetch your appointments.</p>
			</div>


			<!-- Error -->
			<div v-else-if="error" class="state-card error-state">
				<div class="state-icon">!</div>
				<h3>Unable to load appointments</h3>
				<p>{{ error }}</p>

				<button class="retry-btn" @click="fetchAppointments">
					Try Again
				</button>
			</div>


			<!-- Empty -->
			<div v-else-if="appointments.length === 0" class="state-card">
				<div class="empty-icon">
					<svg
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="1.7"
					>
						<rect x="3" y="4" width="18" height="17" rx="3" />
						<path d="M16 2v4M8 2v4M3 10h18" />
					</svg>
				</div>

				<h3>No appointments yet</h3>

				<p>
					You don't have any appointments scheduled.
				</p>

				<button
					class="primary-btn"
					@click="goToDoctors"
				>
					Find a Doctor
					<span>→</span>
				</button>
			</div>


			<!-- Appointments -->
			<div v-else>

				<!-- Stats -->
				<section class="stats-grid">

					<div class="stat-card">
						<div class="stat-icon blue">
							<svg
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="1.8"
							>
								<rect x="3" y="4" width="18" height="17" rx="3" />
								<path d="M16 2v4M8 2v4M3 10h18" />
							</svg>
						</div>

						<div>
							<span>Total</span>
							<strong>{{ appointments.length }}</strong>
						</div>
					</div>


					<div class="stat-card">
						<div class="stat-icon teal">
							<svg
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="1.8"
							>
								<path d="M20 6L9 17l-5-5" />
							</svg>
						</div>

						<div>
							<span>Upcoming</span>
							<strong>{{ upcomingAppointments.length }}</strong>
						</div>
					</div>

				</section>


				<!-- Appointment list -->
				<section class="appointments-section">

					<div class="section-heading">
						<div>
							<h2>Your appointments</h2>
							<p>Keep track of your scheduled consultations.</p>
						</div>

						<span class="appointment-count">
							{{ appointments.length }}
							{{ appointments.length === 1 ? 'Appointment' : 'Appointments' }}
						</span>
					</div>


					<div class="appointments-list">

						<router-link
							v-for="appointment in appointments"
							:key="appointment.name || appointment.slot"
							:to="`/show-appointment/${appointment.slot}`"
							class="appointment-link"
						>

							<article class="appointment-card">

								<!-- Doctor -->
								<div class="doctor-section">

									<div class="doctor-avatar">
										{{ getDoctorInitial(appointment.doctor) }}
									</div>

									<div class="doctor-info">
										<span class="label">DOCTOR</span>

										<h3>
											{{ formatDoctorName(appointment.doctor) }}
										</h3>

										<p>
											<span class="verified-dot"></span>
											Healthcare Professional
										</p>
									</div>

								</div>


								<!-- Appointment details -->
								<div class="appointment-details">

									<div class="detail-item">
										<div class="detail-icon">
											<!-- your calendar SVG -->
										</div>

										<div>
											<span>Date</span>

											<strong>
												{{ formatDate(appointment.appointment_date) }}
											</strong>
										</div>
									</div>


									<div class="detail-item">
										<div class="detail-icon">
											<!-- your clock SVG -->
										</div>

										<div>
											<span>Time</span>

											<strong>
												{{ formatTime(appointment.appointment_time) }}
											</strong>
										</div>
									</div>


									<div class="detail-item">
										<div class="detail-icon">
											<!-- your slot SVG -->
										</div>

										<div>
											<span>Slot</span>

											<strong>
												{{ appointment.slot }}
											</strong>
										</div>
									</div>

								</div>


								<!-- Status -->
								<div class="appointment-status">

									<span class="status-badge">
										<span></span>

										{{ isUpcoming(appointment) ? 'Upcoming' : 'Completed' }}
									</span>

								</div>

							</article>

						</router-link>

					</div>

				</section>

			</div>

		</div>
	</div>
</template>


<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { call } from "../api";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const router = useRouter();

const appointments = ref([]);
const loading = ref(false);
const error = ref(null);


async function fetchAppointments() {
	loading.value = true;
	error.value = null;

	try {
		const res = await call(
			"docbook.api.appointment.list_appointment",
			{
				patient: auth.user.email
			}
		);

		appointments.value = res || [];

		console.log(appointments.value);
	} catch (err) {
		console.error(err);
		error.value = "Unable to load your appointments.";
	} finally {
		loading.value = false;
	}
}


const upcomingAppointments = computed(() => {
	return appointments.value.filter(appointment =>
		isUpcoming(appointment)
	);
});


function isUpcoming(appointment) {
	if (!appointment.appointment_date) {
		return false;
	}

	const appointmentDate = new Date(
		`${appointment.appointment_date}T${appointment.appointment_time || "00:00:00"}`
	);

	return appointmentDate >= new Date();
}


function formatDate(date) {
	if (!date) return "-";

	return new Date(`${date}T00:00:00`).toLocaleDateString(
		"en-IN",
		{
			day: "2-digit",
			month: "short",
			year: "numeric"
		}
	);
}


function formatTime(time) {
	if (!time) return "-";

	const [hours, minutes] = time.split(":");

	const date = new Date();
	date.setHours(Number(hours));
	date.setMinutes(Number(minutes));

	return date.toLocaleTimeString("en-IN", {
		hour: "numeric",
		minute: "2-digit"
	});
}


function formatDoctorName(email) {
	if (!email) return "Doctor";

	const username = email.split("@")[0];

	return username
		.split(/[._-]/)
		.map(word =>
			word.charAt(0).toUpperCase() + word.slice(1)
		)
		.join(" ");
}


function getDoctorInitial(email) {
	const name = formatDoctorName(email);

	return name.charAt(0).toUpperCase();
}


function goToDoctors() {
	router.push("/find-doctors");
}


onMounted(() => {
	fetchAppointments();
});
</script>


<style scoped>
.appointments-page {
	min-height: 100vh;
	background: #f4f7fb;
	position: relative;
	overflow: hidden;
	padding: 50px 24px 80px;
	color: #0f172a;
}

.bg-orb {
	position: fixed;
	border-radius: 50%;
	filter: blur(80px);
	opacity: 0.35;
	pointer-events: none;
}

.orb-blue {
	width: 360px;
	height: 360px;
	background: #bfdbfe;
	top: -120px;
	right: -100px;
}

.orb-teal {
	width: 320px;
	height: 320px;
	background: #99f6e4;
	bottom: -100px;
	left: -120px;
}

.page-container {
	width: min(1100px, 100%);
	margin: 0 auto;
	position: relative;
	z-index: 1;
}


/* Header */

.page-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-bottom: 35px;
}

.eyebrow {
	display: flex;
	align-items: center;
	gap: 8px;
	font-size: 12px;
	font-weight: 700;
	letter-spacing: 1.5px;
	color: #2563eb;
	margin-bottom: 10px;
}

.eyebrow-dot {
	width: 7px;
	height: 7px;
	border-radius: 50%;
	background: #14b8a6;
}

.page-header h1 {
	font-size: clamp(30px, 4vw, 44px);
	line-height: 1.1;
	margin: 0 0 12px;
	font-weight: 750;
	letter-spacing: -1.5px;
}

.page-header p {
	margin: 0;
	color: #64748b;
	font-size: 16px;
	max-width: 560px;
	line-height: 1.6;
}

.header-icon {
	width: 72px;
	height: 72px;
	border-radius: 22px;
	display: flex;
	align-items: center;
	justify-content: center;
	background: rgba(255, 255, 255, 0.65);
	border: 1px solid rgba(255, 255, 255, 0.9);
	box-shadow: 0 15px 35px rgba(15, 23, 42, 0.08);
	backdrop-filter: blur(20px);
	color: #2563eb;
}

.header-icon svg {
	width: 32px;
	height: 32px;
}


/* Stats */

.stats-grid {
	display: grid;
	grid-template-columns: repeat(2, 1fr);
	gap: 18px;
	margin-bottom: 32px;
	max-width: 600px;
}

.stat-card {
	display: flex;
	align-items: center;
	gap: 16px;
	padding: 20px;
	border-radius: 20px;
	background: rgba(255, 255, 255, 0.65);
	border: 1px solid rgba(255, 255, 255, 0.9);
	box-shadow: 0 12px 35px rgba(15, 23, 42, 0.06);
	backdrop-filter: blur(20px);
}

.stat-icon {
	width: 48px;
	height: 48px;
	border-radius: 15px;
	display: flex;
	align-items: center;
	justify-content: center;
}

.stat-icon svg {
	width: 22px;
	height: 22px;
}

.stat-icon.blue {
	background: #dbeafe;
	color: #2563eb;
}

.stat-icon.teal {
	background: #ccfbf1;
	color: #0f766e;
}

.stat-card span {
	display: block;
	color: #64748b;
	font-size: 13px;
	margin-bottom: 3px;
}

.stat-card strong {
	font-size: 24px;
}


/* Section */

.appointments-section {
	margin-top: 10px;
}

.section-heading {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 20px;
	margin-bottom: 18px;
}

.section-heading h2 {
	margin: 0 0 5px;
	font-size: 21px;
}

.section-heading p {
	margin: 0;
	color: #64748b;
	font-size: 14px;
}

.appointment-count {
	padding: 8px 13px;
	border-radius: 999px;
	background: #e0f2fe;
	color: #0369a1;
	font-size: 12px;
	font-weight: 700;
	white-space: nowrap;
}


/* Appointment card */

.appointments-list {
	display: flex;
	flex-direction: column;
	gap: 16px;
}

.appointment-card {
	display: grid;
	grid-template-columns: 1.3fr 2fr auto;
	align-items: center;
	gap: 25px;
	padding: 23px;
	border-radius: 24px;
	background: rgba(255, 255, 255, 0.72);
	border: 1px solid rgba(255, 255, 255, 0.95);
	box-shadow: 0 15px 40px rgba(15, 23, 42, 0.07);
	backdrop-filter: blur(22px);
	transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.appointment-card:hover {
	transform: translateY(-3px);
	box-shadow: 0 20px 45px rgba(15, 23, 42, 0.11);
}


/* Doctor */

.doctor-section {
	display: flex;
	align-items: center;
	gap: 14px;
	min-width: 0;
}

.doctor-avatar {
	width: 58px;
	height: 58px;
	border-radius: 18px;
	flex-shrink: 0;
	display: flex;
	align-items: center;
	justify-content: center;
	background: linear-gradient(135deg, #2563eb, #14b8a6);
	color: white;
	font-size: 21px;
	font-weight: 700;
	box-shadow: 0 10px 22px rgba(37, 99, 235, 0.2);
}

.doctor-info {
	min-width: 0;
}

.doctor-info .label {
	display: block;
	font-size: 10px;
	font-weight: 700;
	letter-spacing: 1.2px;
	color: #94a3b8;
	margin-bottom: 5px;
}

.doctor-info h3 {
	margin: 0 0 5px;
	font-size: 17px;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.doctor-info p {
	margin: 0;
	font-size: 12px;
	color: #64748b;
	display: flex;
	align-items: center;
	gap: 6px;
}

.verified-dot {
	width: 7px;
	height: 7px;
	border-radius: 50%;
	background: #14b8a6;
}


/* Details */

.appointment-details {
	display: grid;
	grid-template-columns: repeat(3, 1fr);
	gap: 12px;
}

.detail-item {
	display: flex;
	align-items: center;
	gap: 10px;
}

.detail-icon {
	width: 38px;
	height: 38px;
	border-radius: 12px;
	background: #eff6ff;
	color: #2563eb;
	display: flex;
	align-items: center;
	justify-content: center;
	flex-shrink: 0;
}

.detail-icon svg {
	width: 18px;
	height: 18px;
}

.detail-item span {
	display: block;
	font-size: 11px;
	color: #94a3b8;
	margin-bottom: 3px;
}

.detail-item strong {
	font-size: 13px;
	white-space: nowrap;
}


/* Status */

.appointment-status {
	display: flex;
	justify-content: flex-end;
}

.status-badge {
	display: inline-flex;
	align-items: center;
	gap: 7px;
	padding: 8px 11px;
	border-radius: 999px;
	background: #ecfdf5;
	color: #047857;
	font-size: 11px;
	font-weight: 700;
	white-space: nowrap;
}

.status-badge span {
	width: 6px;
	height: 6px;
	border-radius: 50%;
	background: #10b981;
}


/* States */

.state-card {
	min-height: 300px;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	text-align: center;
	padding: 40px;
	border-radius: 28px;
	background: rgba(255, 255, 255, 0.68);
	border: 1px solid rgba(255, 255, 255, 0.9);
	box-shadow: 0 15px 40px rgba(15, 23, 42, 0.07);
	backdrop-filter: blur(20px);
}

.state-card h3 {
	margin: 18px 0 7px;
	font-size: 20px;
}

.state-card p {
	margin: 0;
	color: #64748b;
	font-size: 14px;
}

.empty-icon {
	width: 65px;
	height: 65px;
	border-radius: 20px;
	display: flex;
	align-items: center;
	justify-content: center;
	background: #dbeafe;
	color: #2563eb;
}

.empty-icon svg {
	width: 30px;
	height: 30px;
}

.state-icon {
	width: 55px;
	height: 55px;
	border-radius: 50%;
	display: flex;
	align-items: center;
	justify-content: center;
	background: #fee2e2;
	color: #dc2626;
	font-size: 24px;
	font-weight: 700;
}

.retry-btn,
.primary-btn {
	border: none;
	cursor: pointer;
	margin-top: 22px;
	padding: 12px 18px;
	border-radius: 12px;
	font-weight: 600;
}

.retry-btn {
	background: #2563eb;
	color: white;
}

.primary-btn {
	display: inline-flex;
	align-items: center;
	gap: 10px;
	background: #2563eb;
	color: white;
	box-shadow: 0 10px 25px rgba(37, 99, 235, 0.2);
}

.primary-btn:hover,
.retry-btn:hover {
	background: #1d4ed8;
}

.loader {
	width: 38px;
	height: 38px;
	border-radius: 50%;
	border: 3px solid #dbeafe;
	border-top-color: #2563eb;
	animation: spin 0.8s linear infinite;
}

@keyframes spin {
	to {
		transform: rotate(360deg);
	}
}


/* Tablet */

@media (max-width: 900px) {
	.appointment-card {
		grid-template-columns: 1fr;
		gap: 20px;
	}

	.appointment-status {
		justify-content: flex-start;
	}

	.appointment-details {
		grid-template-columns: repeat(3, 1fr);
	}
}


/* Mobile */

@media (max-width: 640px) {
	.appointments-page {
		padding: 30px 16px 60px;
	}

	.page-header {
		margin-bottom: 25px;
	}

	.header-icon {
		width: 54px;
		height: 54px;
		border-radius: 17px;
	}

	.header-icon svg {
		width: 25px;
		height: 25px;
	}

	.page-header h1 {
		font-size: 30px;
	}

	.page-header p {
		font-size: 14px;
	}

	.stats-grid {
		grid-template-columns: 1fr;
		gap: 12px;
	}

	.stat-card {
		padding: 16px;
	}

	.section-heading {
		align-items: flex-start;
		flex-direction: column;
		gap: 10px;
	}

	.appointment-card {
		padding: 18px;
		border-radius: 20px;
	}

	.appointment-details {
		grid-template-columns: 1fr;
		gap: 13px;
	}

	.detail-item {
		padding: 8px 0;
	}

	.doctor-avatar {
		width: 52px;
		height: 52px;
	}
}


/* Very small mobile */

@media (max-width: 400px) {
	.appointments-page {
		padding-left: 12px;
		padding-right: 12px;
	}

	.page-header {
		align-items: flex-start;
	}

	.header-icon {
		display: none;
	}

	.page-header h1 {
		font-size: 27px;
	}

	.appointment-card {
		padding: 15px;
	}
}
</style>