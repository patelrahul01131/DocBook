<template>
	<div>
		<h1>Doctor Appointments</h1>
		<p>Welcome to the doctor appointments dashboard.</p>
	</div>
</template>

<script setup>
import { call } from "../../api.js";

const doctor_name = "bhagyesh";
const appointments = ref([]);

async function fetchAppointments() {
	const res = await call("docbook.api.appointment.list_appointment", { doctor: doctor_name });
	console.log(res);
	appointments.value = res || [];
}

fetchAppointments();
</script>
