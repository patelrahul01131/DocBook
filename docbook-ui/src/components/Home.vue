<script setup>
import {
	Badge,
	Button,
	Combobox,
	toast
} from 'frappe-ui'

import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { call } from '../api'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()

const router = useRouter()

const doctors = ref([])
const selectedDoctor = ref(null)
const loading = ref(false)
const error = ref(null)


// ----------------------------------
// Fetch doctors
// ----------------------------------

const fetchDoctors = async () => {
	loading.value = true
	error.value = null

	try {
		const data = await call(
			'docbook.api.doctor.list_doctors'
		)

		doctors.value = data.map(doctor => ({
			label: doctor.full_name,
			value: doctor.user,
			specialty: doctor.specialty,
			qualification: doctor.qualification,
			phone: doctor.phone
		}))
	} catch (err) {
		console.error(err)
		error.value = 'Unable to load doctors.'
	} finally {
		loading.value = false
	}
}


// ----------------------------------
// Selected doctor
// ----------------------------------

const selectedDoctorData = computed(() => {
	return doctors.value.find(
		doctor => doctor.value === selectedDoctor.value
	)
})


// ----------------------------------
// View doctor
// ----------------------------------

function viewDoctor() {
	if (!selectedDoctor.value) {
		router.push('/doctor_profile')
		return
	}

	router.push({
		path: '/doctor_profile',
		query: {
			doctor: selectedDoctor.value
		}
	})
}


// ----------------------------------
// Find doctors
// ----------------------------------

function findDoctors() {
	router.push('/find-doctors')
}


onMounted(() => {
	fetchDoctors()
})
</script>


<template>

	<div class="home-page">

		<!-- =====================================
		     BACKGROUND DECORATION
		====================================== -->

		<div class="background-orb orb-blue"></div>
		<div class="background-orb orb-teal"></div>


		<!-- =====================================
		     HERO
		====================================== -->

		<section class="hero-section">

			<div class="hero-container">

				<!-- Hero Content -->

				<div class="hero-content">

					<h1>
						Find the right
						<br />

						<span>
							doctor for you.
						</span>
					</h1>

					<p class="hero-description">
						Discover trusted doctors and book your
						appointment quickly and easily.
					</p>


					<!-- Search Card -->

					<div class="search-card">

						<div class="search-header">
							<div class="search-icon">
								<span class="lucide-search size-5" />
							</div>

							<div>
								<h3>
									Find your doctor
								</h3>

								<p>
									Search from available doctors
								</p>
							</div>
						</div>


						<div class="search-controls">

							<div class="combobox-wrapper">

								<Combobox
									v-model="selectedDoctor"
									:options="doctors"
									label="Doctor"
									placeholder="Search doctor..."
									option-label="label"
									:disabled="loading"
								/>

							</div>


							<Button
								class="view-button"
								label="View Doctor"
								icon-left="lucide-arrow-right"
								:disabled="!selectedDoctor"
								@click="viewDoctor"
							/>

						</div>


						<!-- Loading -->

						<div
							v-if="loading"
							class="status-message"
						>
							<span
								class="lucide-loader-circle size-4 animate-spin"
							/>

							Loading doctors...
						</div>


						<!-- Error -->

						<div
							v-if="error"
							class="error-message"
						>
							<span class="lucide-circle-alert size-4" />
							{{ error }}
						</div>


						<!-- Count -->

						<div
							v-if="!loading && !error"
							class="doctor-count"
						>
							<span class="lucide-users size-3.5" />

							{{ doctors.length }}
							doctors available
						</div>

					</div>


					<!-- Trust Items -->

					<div class="trust-items">

						<div>
							<span class="lucide-circle-check"></span>
							Verified doctors
						</div>

						<div>
							<span class="lucide-circle-check"></span>
							Easy booking
						</div>

						<div>
							<span class="lucide-circle-check"></span>
							Simple appointments
						</div>

					</div>

				</div>


				<!-- =====================================
				     HERO VISUAL
				====================================== -->

				<div class="hero-visual">

					<div class="image-wrapper">

						<img
							src="https://images.unsplash.com/photo-1559839734-2b71ea197ec2?auto=format&fit=crop&w=900&q=80"
							alt="Doctor"
						/>


						<!-- Image Overlay -->

						<div class="image-overlay"></div>


						<!-- Floating Doctor Card -->

						<div class="floating-doctor-card">

							<div class="floating-avatar">
								<span class="lucide-stethoscope size-5" />
							</div>

							<div class="floating-info">

								<strong>
									{{ selectedDoctorData?.label || 'Find your specialist' }}
								</strong>

								<span>
									{{ selectedDoctorData?.specialty || 'Choose from available doctors' }}
								</span>

							</div>

							<div
								v-if="selectedDoctorData"
								class="floating-check"
							>
								✓
							</div>

						</div>



					</div>

				</div>

			</div>

		</section>


		<!-- =====================================
		     QUICK ACTIONS
		====================================== -->

		<section class="quick-section">

			<div class="content-container">

				<div class="quick-grid">


					<!-- Find Doctor -->

					<button
						class="quick-card"
						@click="findDoctors"
					>

						<div class="quick-card-top">

							<div class="quick-icon blue">
								<span class="lucide-search size-5" />
							</div>

							<span class="lucide-arrow-up-right arrow-icon"></span>

						</div>

						<h3>
							Find a doctor
						</h3>

						<p>
							Browse doctors by specialty and
							expertise.
						</p>

					</button>


					<!-- Appointments -->

					<button
						class="quick-card"
						@click="router.push('/my-appointments')"
					>

						<div class="quick-card-top">

							<div class="quick-icon teal">
								<span class="lucide-calendar-check size-5" />
							</div>

							<span class="lucide-arrow-up-right arrow-icon"></span>

						</div>

						<h3>
							My appointments
						</h3>

						<p>
							View your upcoming and previous
							appointments.
						</p>

					</button>


					<!-- Doctors -->

					<div class="quick-card">

						<div class="quick-card-top">

							<div class="quick-icon purple">
								<span class="lucide-users size-5" />
							</div>

							<span class="doctor-status-dot"></span>

						</div>

						<h3>
							Doctors available
						</h3>

						<p>

							<span v-if="loading">
								Loading...
							</span>

							<span v-else>
								{{ doctors.length }}
								doctors ready to help you.
							</span>

						</p>

					</div>

				</div>

			</div>

		</section>


		<!-- =====================================
		     CTA
		====================================== -->

		<section class="cta-section">

			<div class="content-container">

				<div class="cta-card">

					<div class="cta-glow"></div>

					<div class="cta-content">

						<div class="cta-icon">
							<span class="lucide-heart-pulse size-6" />
						</div>

						<span class="cta-label">
							YOUR HEALTH MATTERS
						</span>

						<h2>
							Ready to take care
							<br class="hidden sm:block" />
							of your health?
						</h2>

						<p>
							Find a doctor and book your next
							appointment with DocBook.
						</p>

						<Button
							label="Find a doctor"
							icon-left="lucide-arrow-right"
							@click="findDoctors"
						/>

					</div>

				</div>

			</div>

		</section>


		<!-- =====================================
		     FOOTER
		====================================== -->

		<footer class="footer">

			<div class="content-container footer-inner">

				<div class="footer-brand">

					<div class="footer-logo">
						<span class="lucide-heart-pulse size-4" />
					</div>

					<div>
						<strong>
							DocBook
						</strong>

						<span>
							Healthcare made simple.
						</span>
					</div>

				</div>


				<div class="footer-links">

					<span>
						Privacy
					</span>

					<span>
						Terms
					</span>

					<span>
						Contact
					</span>

				</div>


				<div class="copyright">
					© 2026 DocBook
				</div>

			</div>

		</footer>

	</div>

</template>


<style scoped>

/* =========================================
   GLOBAL PAGE
========================================= */

.home-page {
	position: relative;
	min-height: 100vh;

	overflow: hidden;

	background:
		radial-gradient(
			circle at 10% 10%,
			rgba(37, 99, 235, 0.08),
			transparent 28%
		),
		radial-gradient(
			circle at 90% 80%,
			rgba(20, 184, 166, 0.08),
			transparent 30%
		),
		#f4f7fb;

	color: #0f172a;
}


/* =========================================
   BACKGROUND ORBS
========================================= */

.background-orb {
	position: absolute;

	width: 330px;
	height: 330px;

	border-radius: 50%;

	filter: blur(90px);

	pointer-events: none;

	opacity: 0.45;
}

.orb-blue {
	top: -150px;
	left: -100px;

	background: rgba(37, 99, 235, 0.16);
}

.orb-teal {
	right: -120px;
	top: 500px;

	background: rgba(20, 184, 166, 0.14);
}


/* =========================================
   COMMON CONTAINER
========================================= */

.content-container {
	position: relative;

	width: 100%;
	max-width: 1180px;

	margin: 0 auto;

	padding-left: 24px;
	padding-right: 24px;
}


/* =========================================
   HERO
========================================= */

.hero-section {
	position: relative;

	z-index: 1;

	padding: 10px 24px 90px;
}

.hero-container {
	width: 100%;
	max-width: 1180px;

	margin: 0 auto;

	display: grid;

	grid-template-columns:
		minmax(0, 1.05fr)
		minmax(380px, 0.95fr);

	align-items: center;

	gap: 70px;
}

.hero-content {
	min-width: 0;
}

.hero-content h1 {
	margin: 22px 0 0;

	font-size: clamp(42px, 5.5vw, 68px);

	line-height: 1.03;

	letter-spacing: -2.8px;

	font-weight: 750;
}

.hero-content h1 span {
	color: #64748b;
}

.hero-description {
	max-width: 590px;

	margin: 24px 0 0;

	color: #64748b;

	font-size: 18px;

	line-height: 1.7;
}


/* =========================================
   SEARCH CARD
========================================= */

.search-card {
	max-width: 680px;

	margin-top: 32px;

	padding: 18px;

	border:
		1px solid rgba(255, 255, 255, 0.85);

	border-radius: 24px;

	background:
		rgba(255, 255, 255, 0.66);

	backdrop-filter: blur(24px);
	-webkit-backdrop-filter: blur(24px);

	box-shadow:
		0 20px 50px rgba(15, 23, 42, 0.08);
}

.search-header {
	display: flex;

	align-items: center;

	gap: 12px;

	margin-bottom: 14px;
}

.search-icon {
	width: 42px;
	height: 42px;

	display: flex;

	align-items: center;
	justify-content: center;

	border-radius: 13px;

	background: rgba(37, 99, 235, 0.1);

	color: #2563eb;
}

.search-header h3 {
	margin: 0;

	font-size: 14px;

	font-weight: 700;
}

.search-header p {
	margin: 2px 0 0;

	color: #94a3b8;

	font-size: 11px;
}

.search-controls {
	display: flex;

	align-items: flex-end;

	gap: 10px;
}

.combobox-wrapper {
	min-width: 0;

	flex: 1;
}

.view-button {
	min-height: 48px;
}

.status-message,
.error-message,
.doctor-count {
	display: flex;

	align-items: center;

	gap: 7px;

	margin-top: 10px;

	padding-left: 3px;

	font-size: 11px;
}

.status-message,
.doctor-count {
	color: #64748b;
}

.error-message {
	color: #dc2626;
}


/* =========================================
   TRUST
========================================= */

.trust-items {
	display: flex;

	flex-wrap: wrap;

	gap: 20px;

	margin-top: 22px;

	color: #64748b;

	font-size: 12px;
}

.trust-items div {
	display: flex;

	align-items: center;

	gap: 7px;
}

.trust-items span {
	width: 16px;
	height: 16px;

	color: #10b981;
}


/* =========================================
   HERO IMAGE
========================================= */

.hero-visual {
	position: relative;
}

.image-wrapper {
	position: relative;

	width: 100%;
	max-width: 470px;

	margin: 0 auto;

	aspect-ratio: 4 / 5;

	overflow: hidden;

	border:
		1px solid rgba(255, 255, 255, 0.8);

	border-radius: 34px;

	background: white;

	box-shadow:
		0 30px 70px rgba(15, 23, 42, 0.14);
}

.image-wrapper img {
	width: 100%;
	height: 100%;

	display: block;

	object-fit: cover;
}

.image-overlay {
	position: absolute;

	inset: 0;

	background:
		linear-gradient(
			to top,
			rgba(15, 23, 42, 0.5),
			transparent 50%
		);
}


/* =========================================
   FLOATING DOCTOR CARD
========================================= */

.floating-doctor-card {
	position: absolute;

	left: 20px;
	right: 20px;
	bottom: 20px;

	display: flex;

	align-items: center;

	gap: 12px;

	padding: 15px;

	border:
		1px solid rgba(255, 255, 255, 0.6);

	border-radius: 19px;

	background:
		rgba(255, 255, 255, 0.88);

	backdrop-filter: blur(18px);
	-webkit-backdrop-filter: blur(18px);

	box-shadow:
		0 15px 35px rgba(15, 23, 42, 0.15);
}

.floating-avatar {
	width: 45px;
	height: 45px;

	display: flex;

	align-items: center;
	justify-content: center;

	flex-shrink: 0;

	border-radius: 14px;

	background:
		linear-gradient(
			135deg,
			#2563eb,
			#14b8a6
		);

	color: white;
}

.floating-info {
	display: flex;

	flex-direction: column;

	min-width: 0;

	flex: 1;
}

.floating-info strong {
	overflow: hidden;

	color: #0f172a;

	font-size: 13px;

	text-overflow: ellipsis;

	white-space: nowrap;
}

.floating-info span {
	margin-top: 3px;

	overflow: hidden;

	color: #64748b;

	font-size: 10px;

	text-overflow: ellipsis;

	white-space: nowrap;
}

.floating-check {
	width: 25px;
	height: 25px;

	display: flex;

	align-items: center;
	justify-content: center;

	flex-shrink: 0;

	border-radius: 50%;

	background: #10b981;

	color: white;

	font-size: 12px;

	font-weight: 700;
}


/* =========================================
   VERIFIED FLOATING
========================================= */


.verified-icon {
	width: 31px;
	height: 31px;

	display: flex;

	align-items: center;
	justify-content: center;

	border-radius: 10px;

	background: rgba(16, 185, 129, 0.12);

	color: #059669;

	font-size: 13px;

	font-weight: 700;
}

.verified-floating div {
	display: flex;

	flex-direction: column;
}

.verified-floating strong {
	font-size: 11px;
}

.verified-floating span {
	margin-top: 2px;

	color: #64748b;

	font-size: 9px;
}


/* =========================================
   QUICK SECTION
========================================= */

.quick-section {
	position: relative;

	z-index: 1;

	padding: 0 0 70px;
}

.quick-grid {
	display: grid;

	grid-template-columns:
		repeat(3, minmax(0, 1fr));

	gap: 16px;
}

.quick-card {
	position: relative;

	min-width: 0;

	padding: 24px;

	text-align: left;

	border:
		1px solid rgba(255, 255, 255, 0.8);

	border-radius: 22px;

	background:
		rgba(255, 255, 255, 0.62);

	backdrop-filter: blur(20px);

	box-shadow:
		0 12px 35px rgba(15, 23, 42, 0.05);

	cursor: pointer;

	transition:
		transform 0.2s ease,
		box-shadow 0.2s ease,
		background 0.2s ease;
}

.quick-card:hover {
	transform: translateY(-4px);

	background:
		rgba(255, 255, 255, 0.82);

	box-shadow:
		0 20px 40px rgba(15, 23, 42, 0.08);
}

.quick-card-top {
	display: flex;

	align-items: center;

	justify-content: space-between;
}

.quick-icon {
	width: 46px;
	height: 46px;

	display: flex;

	align-items: center;
	justify-content: center;

	border-radius: 14px;
}

.quick-icon.blue {
	background: rgba(37, 99, 235, 0.1);

	color: #2563eb;
}

.quick-icon.teal {
	background: rgba(20, 184, 166, 0.1);

	color: #0f766e;
}

.quick-icon.purple {
	background: rgba(139, 92, 246, 0.1);

	color: #7c3aed;
}

.arrow-icon {
	color: #94a3b8;

	transition: 0.2s ease;
}

.quick-card:hover .arrow-icon {
	color: #2563eb;

	transform: translate(2px, -2px);
}

.quick-card h3 {
	margin: 20px 0 0;

	font-size: 15px;

	font-weight: 700;
}

.quick-card p {
	margin: 7px 0 0;

	color: #64748b;

	font-size: 12px;

	line-height: 1.6;
}

.doctor-status-dot {
	width: 9px;
	height: 9px;

	border-radius: 50%;

	background: #10b981;

	box-shadow:
		0 0 0 5px rgba(16, 185, 129, 0.1);
}


/* =========================================
   CTA
========================================= */

.cta-section {
	position: relative;

	z-index: 1;

	padding: 20px 0 90px;
}

.cta-card {
	position: relative;

	overflow: hidden;

	border-radius: 30px;

	background:
		linear-gradient(
			135deg,
			#0f172a,
			#172554
		);

	color: white;

	box-shadow:
		0 25px 60px rgba(15, 23, 42, 0.16);
}

.cta-glow {
	position: absolute;

	width: 300px;
	height: 300px;

	right: -100px;
	top: -140px;

	border-radius: 50%;

	background: rgba(20, 184, 166, 0.25);

	filter: blur(50px);
}

.cta-content {
	position: relative;

	z-index: 1;

	display: flex;

	flex-direction: column;

	align-items: center;

	padding: 65px 30px;

	text-align: center;
}

.cta-icon {
	width: 52px;
	height: 52px;

	display: flex;

	align-items: center;
	justify-content: center;

	border-radius: 16px;

	background: rgba(255, 255, 255, 0.1);

	color: #5eead4;
}

.cta-label {
	margin-top: 18px;

	color: #5eead4;

	font-size: 10px;

	font-weight: 700;

	letter-spacing: 1.5px;
}

.cta-content h2 {
	margin: 10px 0 0;

	font-size: clamp(28px, 4vw, 42px);

	line-height: 1.15;

	letter-spacing: -1px;
}

.cta-content p {
	max-width: 470px;

	margin: 15px 0 25px;

	color: #94a3b8;

	font-size: 13px;

	line-height: 1.7;
}


/* =========================================
   FOOTER
========================================= */

.footer {
	position: relative;

	z-index: 1;

	border-top:
		1px solid rgba(226, 232, 240, 0.8);
}

.footer-inner {
	display: flex;

	align-items: center;

	justify-content: space-between;

	gap: 20px;

	padding-top: 25px;
	padding-bottom: 25px;
}

.footer-brand {
	display: flex;

	align-items: center;

	gap: 10px;
}

.footer-logo {
	width: 34px;
	height: 34px;

	display: flex;

	align-items: center;
	justify-content: center;

	border-radius: 10px;

	background:
		linear-gradient(
			135deg,
			#2563eb,
			#14b8a6
		);

	color: white;
}

.footer-brand div:last-child {
	display: flex;

	flex-direction: column;
}

.footer-brand strong {
	font-size: 12px;
}

.footer-brand span {
	margin-top: 2px;

	color: #94a3b8;

	font-size: 9px;
}

.footer-links {
	display: flex;

	gap: 20px;

	color: #64748b;

	font-size: 11px;
}

.footer-links span {
	cursor: pointer;

	transition: color 0.2s ease;
}

.footer-links span:hover {
	color: #2563eb;
}

.copyright {
	color: #94a3b8;

	font-size: 10px;
}


/* =========================================
   TABLET
========================================= */

@media (max-width: 1000px) {

	.hero-container {
		grid-template-columns: 1fr;

		gap: 50px;
	}

	.hero-content {
		max-width: 750px;

		margin: 0 auto;
	}

	.hero-visual {
		display: flex;

		justify-content: center;
	}

	.image-wrapper {
		max-width: 500px;
	}

	.verified-floating {
		right: -15px;
	}

}


/* =========================================
   SMALL TABLET
========================================= */

@media (max-width: 700px) {

	.hero-section {
		padding: 55px 18px 65px;
	}

	.content-container {
		padding-left: 18px;
		padding-right: 18px;
	}

	.hero-content h1 {
		font-size: clamp(38px, 11vw, 54px);

		letter-spacing: -2px;
	}

	.hero-description {
		font-size: 16px;
	}

	.quick-grid {
		grid-template-columns: 1fr;
	}

	.search-controls {
		flex-direction: column;

		align-items: stretch;
	}

	.view-button {
		width: 100%;
	}

	.verified-floating {
		right: 12px;

		transform: scale(0.9);

		transform-origin: top right;
	}

	.footer-inner {
		flex-direction: column;

		align-items: flex-start;
	}

}


/* =========================================
   MOBILE
========================================= */

@media (max-width: 500px) {

	.hero-section {
		padding-top: 35px;
	}

	.search-card {
		padding: 14px;

		border-radius: 20px;
	}

	.search-header {
		margin-bottom: 10px;
	}

	.trust-items {
		flex-direction: column;

		gap: 10px;
	}

	.image-wrapper {
		border-radius: 25px;
	}

	.floating-doctor-card {
		left: 12px;
		right: 12px;
		bottom: 12px;

		padding: 12px;
	}

	.floating-avatar {
		width: 39px;
		height: 39px;
	}

	.floating-info strong {
		font-size: 11px;
	}

	.floating-info span {
		font-size: 9px;
	}

	.verified-floating {
		top: 12px;
		right: 10px;

		padding: 8px 10px;
	}

	.verified-icon {
		width: 27px;
		height: 27px;
	}

	.verified-floating strong {
		font-size: 10px;
	}

	.verified-floating span {
		font-size: 8px;
	}

	.quick-card {
		padding: 20px;

		border-radius: 19px;
	}

	.cta-card {
		border-radius: 24px;
	}

	.cta-content {
		padding: 48px 20px;
	}

	.footer-links {
		gap: 14px;
	}

	.copyright {
		order: 3;
	}

}


/* =========================================
   VERY SMALL MOBILE
========================================= */

@media (max-width: 360px) {

	.hero-content h1 {
		font-size: 36px;
	}

	.doctor-count {
		font-size: 10px;
	}

	.floating-doctor-card {
		left: 8px;
		right: 8px;
	}

	.verified-floating {
		display: none;
	}

}

</style>