<template>
	<div class="coords-container">
	  <span class="coords">X: {{coords.x}} </span>
	  <span class="coords">Y: {{coords.y}} </span>
	  <span class="coords">Z: {{coords.z}} </span>
		<span class="coords">A: {{coords.a}} </span>
		<span class="coords">B: {{coords.b}} </span>
	</div>
</template>

<script>
	export default {
	  name: 'DeckSlot',
	  computed: {
			coords() {
				let coords = this.$store.state.coordinates
				for (var coord in coords) {
					coords[coord] = Math.floor(coords[coord] * 100) / 100
				}
				return coords
			}
		}
	}
</script>
