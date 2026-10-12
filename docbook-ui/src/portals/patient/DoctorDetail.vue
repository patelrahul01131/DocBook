<script setup>
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

onMounted(() => {
  const doctorId = route.params.id
  if (doctorId) {
    router.replace({ path: '/doctor_profile', query: { doctor: doctorId } })
  } else {
    router.replace('/doctor-profile-booking')
  }
})
</script>

<template>
  <div class="flex items-center justify-center min-h-[60vh] text-slate-500 text-sm">
    <span class="animate-spin mr-2">⏳</span> Loading doctor profile...
  </div>
</template>
