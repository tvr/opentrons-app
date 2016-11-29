<template>
  <span>
    <input ref='code'></input><button @click='execCode'>Exec</button>
    <section id='task-pane' v-show='!running'>
      <aside id='step-list'>
        <StepList></StepList>
      </aside>
      <router-view :class="{'disabled': busy}"></router-view>
    </section>
    <RunScreen v-show='running'></RunScreen>
  </span>
</template>

<script>
  import StepList from './StepList.vue'
  import RunScreen from './RunScreen.vue'

  export default {
    props: ['busy'],
    components: {
      StepList,
      RunScreen
    },
    computed: {
      running () {
        return this.$store.state.running || this.$store.state.protocolFinished
      }
    },
    methods: {
      execCode () {
        let code = this.$refs.code.value
        console.log(code)
        this.$http.get('http://localhost:31950/exec?' + code).then((response) => {
          console.log(response)
        })
      }
    }
  }
</script>
