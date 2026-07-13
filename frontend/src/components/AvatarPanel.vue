<script setup lang="ts">
defineProps<{
  speaking?: boolean
  statusText?: string
}>()
</script>

<template>
  <div class="avatar-panel">
    <div class="avatar-ring" :class="{ speaking }">
      <div class="avatar-face">
        <div class="eyes">
          <span class="eye" /><span class="eye" />
        </div>
        <div class="mouth" :class="{ speaking }" />
      </div>
    </div>
    <div class="avatar-info">
      <h3>冷链合规顾问</h3>
      <p class="role">医药冷链 · 数字人助手</p>
      <p class="status" :class="{ active: speaking }">
        {{ statusText || '在线待命' }}
      </p>
    </div>
    <div class="badges">
      <span class="badge">GSP</span>
      <span class="badge">GB/T</span>
      <span class="badge">RAG</span>
    </div>
  </div>
</template>

<style scoped>
.avatar-panel {
  text-align: center;
  padding: 1.5rem 1rem;
}

.avatar-ring {
  width: 120px;
  height: 120px;
  margin: 0 auto 1rem;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-accent), var(--color-primary-light));
  padding: 4px;
  transition: box-shadow 0.3s;
}

.avatar-ring.speaking {
  animation: pulse 1.5s ease-in-out infinite;
  box-shadow: 0 0 20px rgba(34, 211, 238, 0.5);
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 10px rgba(34, 211, 238, 0.3); }
  50% { box-shadow: 0 0 25px rgba(34, 211, 238, 0.6); }
}

.avatar-face {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: linear-gradient(180deg, #e0f2fe 0%, #bae6fd 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
}

.eyes {
  display: flex;
  gap: 1.25rem;
}

.eye {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--color-primary);
}

.mouth {
  width: 24px;
  height: 4px;
  border-radius: 2px;
  background: var(--color-primary);
  transition: all 0.2s;
}

.mouth.speaking {
  height: 12px;
  border-radius: 50%;
  animation: talk 0.4s ease-in-out infinite alternate;
}

@keyframes talk {
  from { transform: scaleY(0.6); }
  to { transform: scaleY(1.2); }
}

.avatar-info h3 {
  font-size: 1rem;
  color: var(--color-primary);
  margin-bottom: 0.25rem;
}

.role {
  font-size: 0.8rem;
  color: var(--color-text-muted);
}

.status {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  margin-top: 0.5rem;
  padding: 0.25rem 0.75rem;
  background: var(--color-bg);
  border-radius: 20px;
  display: inline-block;
}

.status.active {
  color: var(--color-primary);
  background: var(--color-accent-soft);
}

.badges {
  display: flex;
  justify-content: center;
  gap: 0.5rem;
  margin-top: 1rem;
}

.badge {
  font-size: 0.65rem;
  font-weight: 600;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  background: var(--color-primary);
  color: #fff;
  letter-spacing: 0.03em;
}
</style>
