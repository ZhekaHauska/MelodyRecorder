const recordAudio = () =>
  new Promise(async resolve => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mediaRecorder = new MediaRecorder(stream);
    const audioChunks = [];

    mediaRecorder.addEventListener("dataavailable", event => {
      audioChunks.push(event.data);
    });

    const start = () => mediaRecorder.start();

    const stop = () =>
      new Promise(resolve => {
        mediaRecorder.addEventListener("stop", () => {
          const audioBlob = new Blob(audioChunks);
          const audioUrl = URL.createObjectURL(audioBlob);
          const audio = new Audio(audioUrl);
          const play = () => audio.play();
          resolve({ audioBlob, audioUrl, play });
        });

        mediaRecorder.stop();
      });

    resolve({ start, stop });
  });

const sleep = time => new Promise(resolve => setTimeout(resolve, time));

const handleAction = async () => {
  const recorder = await recordAudio();
  const actionButton = document.getElementById('action');
  actionButton.disabled = true;
  recorder.start();
  await sleep(10000);
  const audio = await recorder.stop();
  try {
      const response = await fetch(`http://localhost:5000/process`, {method: "POST", body: audio.audioBlob});
      const result = await response.json();
      console.log('Успех:', JSON.stringify(result));
  } catch (error){
      console.error('Ошибка:', error);
  }

  actionButton.disabled = false;

  window.location.reload();
}

