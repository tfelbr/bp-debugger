<script lang="ts">
    import { browser } from '$app/environment'
    import Button, { Label, Icon } from "@smui/button"
    import SelectedEventList from '../components/SelectedEventList.svelte';
    import SystemStateTable from '../components/SystemStateTable.svelte';
    import Slider from '@smui/slider';
    import BreakPoints from '../components/BreakPoints.svelte';
    import ParameterTable from '../components/ParameterTable.svelte';

    let to_display: number = -1;  // event id
    let data_type: "current" | "imported" = "current";
    let parameters_to_display = -1; // index of parameter array
    let parameters_to_display_offset = 1;
    let timeout: number = 0;
    let running = false;
    let ended = false;

    let data: TracePayload[] = [];
    let imported_data: TracePayload[] = [];
    let parameters: ParameterInfo[] = [];
    let imported_parameters: ParameterInfo[] = [];
    let breakpoints_to_highlight: string[] = [];
    let files: FileList;
    let display_parameters = false; // show parameters or not
    let selected = "";  // selected event name

    function pause(): void {
      fetch("/pause")
    }

    function step(): void {
      fetch("/step")
    }

    function handle_display_running(): void {
      parameters_to_display = data.length - 1 + parameters_to_display_offset
      if (running) {
        data_type = "current"
        to_display = -1
        breakpoints_to_highlight = []
      } else {
        to_display = data.length - 1
      }
    }

    function display_callback(display: number, type: "current" | "imported"): void {
      if (type === "current") {
        parameters_to_display_offset = 1
        selected = data[display].selected
      }
      else {
        parameters_to_display_offset = 0
        selected = imported_data[display].selected
      }
      data_type = type
      to_display = display
      parameters_to_display = to_display + parameters_to_display_offset
    }

    function start(): void {
      fetch("/continue")
      running = true;
      handle_display_running()
    }

    async function download(file_type: "json" | "emf"): Promise<void> {
      if (file_type === "json") {
        // copied from https://www.programonaut.com/how-to-create-a-download-for-a-zip-file-with-sveltekit-step-by-step/
        // get zip file from endpoint
        let res = await fetch("/download/json", {
          method: 'GET',
        });
        // convert json file to url object (for anchor tag download)
        let blob = await res.blob();
        let url = window.URL || window.webkitURL;
        let link = url.createObjectURL(blob);

        // generate anchor tag, click it for download and then remove it again
        let a = document.createElement("a");
        a.setAttribute("download", "model.json");
        a.setAttribute("href", link);
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      }
    }

    function klick_upload(): void {
      let file_upload = document.getElementsByName("upload")
      file_upload[0].click()
    }

    async function upload(): Promise<void> {
      let content = await files[0].text()
      imported_data = await (
        await fetch(
          "/upload",
          {
            method: "POST",
            headers: {
              'Accept': 'application/json',
              'Content-Type': 'application/json'
            },
            body: content
          }
        )
      ).json()
    }

    if (browser) {
        // stream events to frontend
        const eventSource = new EventSource("/listen");
        eventSource.onmessage = (event) => {
            let d: TracePayload | InfoPayload | InitialPayload = JSON.parse(event.data);

            if (d.type === "trace") {
              data.push(d);
              parameters.push(d.parameters)
              parameters = parameters;
              handle_display_running()

            } else if (d.type === "info") {
              running = !d.paused
              ended = d.ended
              handle_display_running()
              breakpoints_to_highlight = d.breakpoint_ids

            } else if (d.type === "initial") {
              timeout = d.timeout
              parameters.push(d.parameters)
              parameters = parameters
              parameters_to_display = 0
              running = d.running
            }
            if (!running || timeout > 0) data = data
        }
    }


    $: if (browser) fetch(`/settimeout/${timeout}`)
    $: if (files) upload()
    $: {
      for (let d of imported_data) {
        imported_parameters.push(d.parameters)
      }
    }
    
</script>

<style>
    .container {
      position: relative;
      display: flex;
      height: 90vh;
      max-width: 100vw;
      padding-top: 10px;
      z-index: 0;
    }
  
</style>

<div style="display: flex; height: 5vh; padding-left: 10px;">
  <div>
    <Button variant="raised" on:click={start} disabled={running || ended}>
      <Label>Start</Label>
      <Icon class="material-icons">play_arrow</Icon>
    </Button>
    <Button variant="raised" on:click={pause} disabled={!running || ended}>
      <Label>Pause</Label>
      <Icon class="material-icons">pause</Icon>
    </Button>
    <Button variant="raised" on:click={step} disabled={running || ended}>
      Step
    </Button>
  </div>
  <p style="padding-left: 10px; padding-right: 10px;">Timeout: {timeout}s</p>
  <Slider
    bind:value={timeout}
    disabled={ended}
    style="flex-grow: 1;"
    min={0}
    max={2}
    step={0.1}
  />

  <!-- upload and download -->
  <div>
    <Button variant="raised" disabled={running} on:click={() => download("json")}>
      <Label>
        Download Model
      </Label>
      <Icon class="material-icons">download</Icon>
    </Button>
    <Button variant="raised" disabled={running} on:click={() => klick_upload()}>
      <Label>
        Upload Model
      </Label>
      <Icon class="material-icons">upload</Icon>
    </Button>
  </div>

  <input accept=".json" bind:files={files} type="file" name="upload" style="display: none;"/>
</div>

<div class="container">
  <SelectedEventList 
    events={data} 
    imported_events={imported_data} 
    display_callback={display_callback} 
    running={running}
  />
  <div>
    <SystemStateTable
      selected={selected}
      event_id={to_display} 
      data_type={data_type}
      parameters_existent={display_parameters}
    />
    <ParameterTable 
      parameter_id={parameters_to_display} 
      current_parameters={parameters}
      imported_parameters={imported_parameters}
      data_type={data_type}
      running={running}
      bind:display_parameters={display_parameters}
    />
  </div>
    <BreakPoints running={running} highlight={breakpoints_to_highlight} />
</div>


