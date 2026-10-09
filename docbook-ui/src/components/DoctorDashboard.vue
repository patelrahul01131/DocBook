<template>
	<div class="dashboard-container">
		<h1>Doctor Dashboard</h1>
		<p>Welcome to the doctor dashboard.</p>

		<div class="select-wrapper">
			<label for="doctor-select">Choose a Doctor:</label>
			<select id="doctor-select" v-model="selectedDoctorId">
				<option value="">Select Doctor</option>
				<option v-for="doctor in doctors" :key="doctor.name" :value="doctor.name">
					{{ doctor.full_name || doctor.doctor_name || doctor.name }}
				</option>
			</select>
		</div>

		<div v-if="selectedDoctor" class="doctor-card">
			<h3>{{ selectedDoctor.full_name || selectedDoctor.name }}</h3>
			<p><strong>Specialty:</strong> {{ selectedDoctor.specialty || "General" }}</p>
			<p><strong>Qualification:</strong> {{ selectedDoctor.qualification || "N/A" }}</p>
			<p><strong>Experience:</strong> {{ selectedDoctor.experience_years || 0 }} years</p>
			<p><strong>Consultation Fee:</strong> ${{ selectedDoctor.consultation_fee || 0 }}</p>
			<p><strong>Rating:</strong> ⭐ {{ selectedDoctor.rating || 5.0 }}</p>
		</div>
	</div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { call } from "../api.js";

const doctors = ref([]);
const specialities = doctors; // Backward compatibility alias
const selectedDoctorId = ref("");

const selectedDoctor = computed(() => {
	return doctors.value.find((d) => d.name === selectedDoctorId.value);
});

onMounted(async () => {
	try {
		const res = await call("docbook.api.doctor.list_doctors");
		doctors.value = res || [];
	} catch (error) {
		console.error("Failed to fetch doctors:", error);
	}
});
</script>

<style scoped>
.dashboard-container {
	max-width: 600px;
	margin: 0 auto;
	padding: 20px;
}

.select-wrapper {
	margin: 20px 0;
	display: flex;
	flex-direction: column;
	gap: 8px;
}

select {
	padding: 10px 14px;
	font-size: 16px;
	border: 1px solid #ccc;
	border-radius: 6px;
	background-color: #fff;
	color: #333;
}

.doctor-card {
	margin-top: 20px;
	padding: 16px 20px;
	border: 1px solid #e0e0e0;
	border-radius: 8px;
	background: #fdfdfd;
	box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.doctor-card h3 {
	margin-top: 0;
	margin-bottom: 12px;
	color: #2c3e50;
}

.doctor-card p {
	margin: 6px 0;
	color: #555;
}
</style>
