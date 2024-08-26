//This function is created to mitigate refresh get old value issue
window.onload = function() {
    let counter = 0;
    let limit = 10;
    let selectors = [
        "#refresh_api_gateway_url",
        "#refresh_api_token",
        "#refresh_sagemaker_endpoints",
        "#refresh_sd_checkpoints",
        "#refresh_txt2img_inference_job_ids",
        "#refresh_textual_inversion",
        "#refresh_sagemaker_endpoints_delete"
    ];

    let intervalId = setInterval(function() {
        console.log("click refresh when page reloaded");

        let allElementsFound = true;
        for (let selector of selectors) {
            let element = document.querySelector(selector);
            if (element != null) {
                console.log('click element', element)
                element.click();
            } else {
                allElementsFound = false;
                console.warn(`Could not find element with selector: ${selector}`);
            }
        }

        counter++;
        if (counter === limit || allElementsFound) {
            console.log("refresh time:" + counter);
            clearInterval(intervalId);
        }
    }, 2000);
};

let uploadedFilesMap = new Map();
let chunkSize = 512 * 1024 * 1024; // 200MB chunk size, you can adjust this as needed.
let unitMb = 1000* 1024;
let filButtonClass = 'block gradio-html svelte-90oupt padded hide-container';
let filButtonId = 'file-uploader';

const modelTypeMap = {
    'SD Checkpoints': 'Stable-diffusion',
    'Textual Inversion': 'embeddings',
    'LoRA model': 'Lora',
    'ControlNet model': 'ControlNet',
    'Hypernetwork': 'hypernetworks',
    'VAE': 'VAE'
};

function clearFileInput() {
    var fileInput = document.getElementById('file-uploader');
    var newFileInput = document.createElement('input');
    newFileInput.type = 'file';
    newFileInput.id = filButtonId;
    newFileInput.className = filButtonClass;
    newFileInput.multiple = true;
    newFileInput.style.width = '100%';
    newFileInput.style.marginTop = '25px';
    newFileInput.onchange = showFileName;
    fileInput.parentNode.replaceChild(newFileInput, fileInput);
}

function getModelTypeValue(dropdown_value){
    const typeDom = document.getElementById("model_type_value_ele_id");
    if (modelTypeMap.hasOwnProperty(dropdown_value)) {
        typeDom.value = modelTypeMap[dropdown_value];
    } else {
        // 如果没有找到匹配的值，你可能需要处理这种情况
        console.error("Unsupported dropdown value:", dropdown_value);
    }
    clearFileInput();
    return dropdown_value;
}

function showFileName(event) {
    const fileListDiv = document.getElementById("hidden_bind_upload_files");
    // show file name key
    const typeDom = document.getElementById("model_type_value_ele_id");
    const typeValue = typeDom.value
    if(typeValue == null){
        alert("Please choose model type!")
        return;
    }
    if (uploadedFilesMap.size == 0){
        // uploadedFiles = event.target.files;
        uploadedFilesMap.set(typeValue,event.target.files);
    }else {
        // uploadedFiles.push(...event.target.files);
        if (uploadedFilesMap.has(typeValue)) {
            let existFiles = new Array();
            for (const uploadFile of uploadedFilesMap.get(typeValue)) {
                existFiles.push(uploadFile);
                for (const file of event.target.files) {
                    if (uploadFile.name == file.name && uploadFile.size == file.size) {
                        alert("Duplicate model to upload！");
                        continue;
                    }
                }
            }
            existFiles.push(...event.target.files);
            uploadedFilesMap.set(typeValue, existFiles);
        } else {
            uploadedFilesMap.set(typeValue, event.target.files);
        }
    }
    fileListDiv.innerHTML = "";
    for (let [typeKey, uploadedFiles] of uploadedFilesMap) {
        const fileArray = Array.from(uploadedFiles);
        if(fileArray.length === 0){
            continue;
        }
        const fileItemSpan = document.createElement("span");
        fileItemSpan.innerHTML = `${typeKey}: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`;
        fileListDiv.appendChild(fileItemSpan);


        let map = new Map();
        fileArray.forEach(row => {
          map.set(row.name, row);
        })
        for (let [key, uploadedFile] of map) {
            const fileName = uploadedFile.name;
            const fileSize = uploadedFile.size/unitMb;
            const fileType = uploadedFile.type;
            const fileItemDiv = document.createElement("tr");
            fileItemDiv.innerHTML = `&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Name: ${fileName} | Size: ${fileSize.toFixed(2)} MB | Type: ${fileType} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`;
            const deleteButton = document.createElement("button");
            deleteButton.style.backgroundColor = "#E5E5E5";
            deleteButton.style.border = "1px solid black";
            deleteButton.style.borderRadius = "2px";
            deleteButton.style.float = "right";
            deleteButton.textContent = "DELETE";
            deleteButton.addEventListener("click", () => {
                map.delete(key);
                const parentNode = fileItemDiv.parentNode;
                if (parentNode) {
                    // 判断 fileItemDiv 是否是最后一个元素
                    const isLastChild = Array.from(parentNode.children).indexOf(fileItemDiv) === parentNode.children.length - 1;
                    // 删除对应的 fileItemDiv 和 fileItemSpan
                    parentNode.removeChild(fileItemDiv);
                    if (isLastChild) {
                        parentNode.removeChild(fileItemSpan);
                    }
                }
                // fileListDiv.removeChild(fileItemDiv);
            });
            fileItemDiv.appendChild(deleteButton);
            fileListDiv.appendChild(fileItemDiv);
        }
        uploadedFilesMap.set(typeKey,map.values())
    }
}


function updatePercentProgress(progress) {
    // 根据groupName找到对应的进度条或其他UI元素
    const progressBar = document.getElementById(`progress-percent`);
    // const progressDiv = document.createElement(`div`);
    if (progressBar) {
        progressBar.innerText = `${progress}`;
        // progressBar.innerHTML = progressDiv;
    }
}

function updateProgress(groupName, fileName, progress, part, total) {
    // 根据groupName找到对应的进度条或其他UI元素
    const progressBar = document.getElementById(`progress-bar`);
    const progressDiv = document.createElement(`div`);
    if (progressBar) {
        // 更新进度条的宽度或显示上传百分比
        // progressDiv.style.width = `${progress}%`;
        // progressDiv.innerText = `${groupName}-${fileName}: ${progress.toFixed(2)}%`;
        progressDiv.innerText = `${groupName}-${fileName}: total: ${total} parts, part${part}: finished`;
        progressBar.appendChild(progressDiv)
    }
}

function uploadFileToS3(files, groupName, username) {
    const apiGatewayUrl = document.querySelector("#aws_api_url > label > textarea")?
        document.querySelector("#aws_api_url > label > textarea")["value"]: "";
    const apiToken = document.querySelector("#aws_api_gateway_url_token > label > textarea")?
        document.querySelector("#aws_api_gateway_url_token > label > textarea")["value"]: "";

    if (!apiGatewayUrl) {
        alert("Please load the API URL (ApiGatewayUrl) by click refresh button in API and User Settings tab.");
        return;
    }

    if (!apiToken) {
        alert("Please load the API Token (ApiGatewayUrlToken) by click refresh button in API and User Settings tab.");
        return;
    }

    const presignedUrls = [];
    const filenames = [];
    const fileArrays = [];
    for(const file of files){
        const fileSize = file.size;
        const totalChunks = Math.ceil(fileSize / chunkSize);
        const fileName = file.name;
        const fileParam = {
            filename: fileName,
            parts_number: totalChunks
        }
        fileArrays.push(file);
        filenames.push(fileParam);
    }
    const payload = {
        checkpoint_type: groupName,
        filenames: filenames,
        params: { message: "placeholder for chkpts upload test", "creator": username }
    };
    const apiUrl = apiGatewayUrl.endsWith('/') ? apiGatewayUrl : apiGatewayUrl + '/';
    const apiKey = apiToken;
    const url = apiUrl + "checkpoints";
    fetch(url, {
        method: "POST",
        headers: {
            'x-api-key': apiKey,
            'username': username,
        },
        body: JSON.stringify(payload),
    })
        .then((response) => {
            if (response.status !== 201 && response.status !== 202) {
                return response.json().then(errorData => {
                    throw new Error(errorData.message);
                });
            }
            return response.json();
        })
        .then((data) => {
            data = data.data;
            const presignedUrlList = data.s3PresignUrl;
            const checkpointId = data.checkpoint.id;
            Promise.all(fileArrays.map(file => {
                const presignedUrl = presignedUrlList[file.name];
                // presignedUrls.push(...presignedUrl);
                // return uploadFileChunksWithWorker(file, presignedUrls, checkpointId, groupName, url, apiKey);
                return uploadFileChunks(file, presignedUrl, checkpointId, groupName, url, apiKey);
            })).then(results => {
                 console.log(results);
            }).catch(error => {
                console.error("Error uploading chunks:", error);
                // 处理错误
                alert("Error uploading chunks! Upload stopped, please refresh your UI and retry");
            });
        })
        .catch((error) => {
            console.error(error);
            alert(error);
        });
}

function uploadFileChunks(file, presignedUrls, checkpointId, groupName, url, apiKey) {
    return new Promise((resolve, reject) => {
        const fileSize = file.size;
        const totalChunks = Math.ceil(fileSize / chunkSize);
        if(totalChunks != presignedUrls.length){
            const errorMessage = `Generated presignedUrls do not match totalChunks ${totalChunks} ${presignedUrls.length}`;
            alert(errorMessage);
            reject(new Error(errorMessage));
            return;
        }
        let currentChunk = 0;
        const parts = [];
        // 开始上传第一个分片
        uploadNextChunk();
        function uploadNextChunk() {
            if (currentChunk >= totalChunks) {
                console.log("All chunks uploaded successfully!");
                // 可在此处触发上传完成后的操作
                uploadedFilesMap.clear();
                const payload = {
                    "status": "Active",
                    "multi_parts_tags": {[file.name]: parts}
                }
                fetch(url + '/' + checkpointId, {
                    method: "PUT",
                    headers: {
                        'x-api-key': apiKey
                    },
                    body: JSON.stringify(payload),
                })
                    .then((response) => {
                        console.log(response.json());
                    });
                resolve(payload);
                return;
            }
            const chunk = file.slice(
                currentChunk * chunkSize,
                (currentChunk + 1) * chunkSize
            );
            // 使用Fetch API或XMLHttpRequest将当前分片上传到S3的presigned URL
                        const xhr = new XMLHttpRequest();
            xhr.open("PUT", presignedUrls[currentChunk], true);
            // xhr.setRequestHeader("Content-Type", "application/octet-stream");

            xhr.onload = function () {
                if (xhr.status === 200) {
                    console.log("Chunk uploaded successfully");
                    // Proceed to upload the next chunk or finalize the upload process
                } else {
                    console.error("Chunk upload failed");
                    reject();
                    return;
                }
                const headersString = xhr.getAllResponseHeaders();
                const headersArray = headersString.trim().split("\r\n");
                const headersObject = {};
                headersArray.forEach((header) => {
                    const [name, value] = header.split(": ");
                    headersObject[name] = value;
                });
                const etag = headersObject['etag'];
                console.log(etag)
                console.log(headersObject)
                parts.push({
                    ETag: etag,
                    PartNumber: currentChunk + 1
                });
                currentChunk++;
                const progress = (currentChunk / totalChunks) * 100;
                // 更新进度条的宽度或显示上传百分比
                updateProgress(groupName, file.name, progress, currentChunk, totalChunks);
                uploadNextChunk();
            };
            xhr.onerror = function () {
              console.error("Chunk upload failed");
              reject();
            };

            xhr.upload.onprogress = function (event) {
                // const percentComplete = (event.loaded / event.total) * 100 / totalChunks + currentChunk/totalChunks;
                // console.log(`Upload progress: ${percentComplete.toFixed(2)}%`);
                const bytesUploaded = currentChunk * chunkSize + event.loaded;
                const totalBytes = fileSize;
                const percentComplete = (bytesUploaded / totalBytes) * 100;
              updatePercentProgress(`${percentComplete.toFixed(2)}%`);
            };
            xhr.send(chunk);
        }
    });
}

function uploadFileChunksWithWorker(file, presignedUrls, checkpointId, groupName, url, apiKey) {
    const totalChunks = Math.ceil(file.size / chunkSize);
    const workerPromises = [];
    const parts = [];
    for (let currentChunk = 0; currentChunk < totalChunks; currentChunk++) {
        const chunk = file.slice(
            currentChunk * chunkSize,
            (currentChunk + 1) * chunkSize
        );
        const presignedUrl = presignedUrls[currentChunk];
        // TODO
        const worker = new Worker('http://127.0.0.1:7860/file=extensions/stable-diffusion-aws-extension/javascript/uploadfile.js');
        const promise = new Promise((resolve, reject) => {
            worker.addEventListener('message', function(event) {
                if (event.data.error) {
                    reject(new Error(event.data.error));
                } else {
                    parts.push({
                        ETag: event.data.etag,
                        PartNumber: currentChunk + 1
                    });
                    const progress = (currentChunk + 1) / totalChunks * 100;
                    updateProgress(groupName, file.name, progress, currentChunk, totalChunks);
                    resolve();
                }
                worker.terminate();
            });
            worker.postMessage({
                presignedUrl,
                chunk,
            });
        });
        workerPromises.push(promise);
    }

    return Promise.all(workerPromises)
        .then(() => {
            const payload = {
                "checkpoint_id": checkpointId,
                "status": "Active",
                "multi_parts_tags": { [file.name]: parts }
            };
            fetch(url, {
                method: "PUT",
                headers: {
                    'x-api-key': apiKey
                },
                body: JSON.stringify(payload),
            })
                .then((response) => {
                    console.log(response.json());
                });
            return payload;
        })
        .catch(error => {
            console.error("Error uploading chunks:", error);
            // 可以在这里处理错误情况
            throw error;
        });
}
function uploadFiles() {
    const uploadPromises = [];
    const username = document.querySelector('#invisible_user_name_for_ui > label > textarea')['value']
    for (const [groupName, files] of uploadedFilesMap.entries()) {
        // for (const file of files) {
        //     uploadPromises.push(uploadFileToS3(file, groupName));
        // }
        uploadPromises.push(uploadFileToS3(files, groupName, username));
    }

    Promise.all(uploadPromises)
        .then(() => {
            console.log("All files uploaded successfully!");
            // All files are uploaded, you can perform further actions here if needed.
            return "All files uploaded successfully!"
        })
        .catch((error) => {
            console.error("Error uploading files:", error);
            return "Error uploading files"
            // Handle errors as needed.
        });
}

// Save configuration in txt2img panel
function getDomValue(selector, defaultValue, isTextContent = false) {
    try {
        const element = document.querySelector(selector);
        if (isTextContent) {
            return element.textContent || defaultValue;
        } else {
            return element.value || defaultValue;
        }
    } catch (error) {
        return defaultValue;
    }
}

// Function to get the selected tab inside the img2img
function getSelectedButton() {
    // Get the parent element
    let parentDiv = document.querySelector("#mode_img2img > div.tab-nav.scroll-hide.svelte-1g805jl");

    // Get all the button children
    let buttons = parentDiv.querySelectorAll("button");

    // Initialize a variable to store the selected button
    let selectedButtonIndex = -1;

    // Loop through each button
    for (let i = 0; i < buttons.length; i++) {
        // Check if the button has the 'selected' class
        if (buttons[i].classList.contains("selected")) {
            // Store the index of the selected button (add 1 because nth-child is 1-indexed)
            selectedButtonIndex = i + 1;
            break;
        }
    }

    // Create a mapping from child index to a certain value
    let mapping = {
        1: "img2img",
        2: "Sketch",
        3: "Inpaint",
        4: "Inpaint_sketch",
        5: "Inpaint_upload",
        6: "Batch"
    };

    // Check if a button was selected
    if (selectedButtonIndex != -1) {
        // If yes, return the corresponding value from the mapping
        return mapping[selectedButtonIndex];
    } else {
        // If no button was selected, return a suitable message
        return "No button is selected.";
    }
}

// function to get tab "Restore to" or "Resize by"
function getSelectedTabResize() {
    // Create a mapping from child index to a certain value
    let mapping = {
        1: "ResizeTo",
        2: "ResizeBy"
    };

    // Get the parent element
    let parentDiv = document.querySelector("#component-477 > div.tab-nav.scroll-hide.svelte-1g805jl");
    if(parentDiv == null){
        return mapping[1]
    }

    // Get all the button children
    let buttons = parentDiv.querySelectorAll("button");

    // Initialize a variable to store the selected button
    let selectedButtonIndex = -1;

    // Loop through each button
    for (let i = 0; i < buttons.length; i++) {
        // Check if the button has the 'selected' class
        if (buttons[i].classList.contains("selected")) {
            // Store the index of the selected button (add 1 because nth-child is 1-indexed)
            selectedButtonIndex = i + 1;
            break;
        }
    }



    // Check if a button was selected
    if (selectedButtonIndex != -1) {
        // If yes, return the corresponding value from the mapping
        return mapping[selectedButtonIndex];
    } else {
        // If no button was selected, return a suitable message
        return "No tab is selected.";
    }
}

function set_textbox_value(textboxId, newValue) {
    let textbox = document.querySelector(textboxId);
    console.log("Trying to set the value of textBox")
    if (textbox) {
        textbox.textContent = newValue;
    } else {
        console.log("Textbox with id " + textboxId + " not found.");
    }
}

function set_textbox_value_gradio(elementId, newValue) {
    let textbox = gradioApp().getElementById(elementId).querySelector('p');
    console.log("Trying to set the value of textBox")
    if (textbox) {
        textbox.textContent = newValue;
    } else {
        console.log("Textbox with id " + elementId + " not found.");
    }
}

function inference_job_timepicker_text_change(){
    // 获取日期选择器元素
    const dateStartInput = document.querySelector("#start_timepicker_text");
    const selectedStartDate = dateStartInput.value;
    const dateEndInput = document.querySelector("#end_timepicker_text");
    const selectedEndDate = dateEndInput.value;
    gradioApp().getElementById("start_time_picker_button_hidden").click()
    gradioApp().getElementById("end_time_picker_button_hidden").click()
    gradioApp().getElementById("start_time_picker_button_hidden").value = selectedStartDate
    gradioApp().getElementById("end_time_picker_button_hidden").value= selectedEndDate
}

function get_time_button_value(){
    const dateStartInput = document.querySelector("#start_timepicker_text");
    const selectedStartDate = dateStartInput.value;
    dateStartInput.setAttribute("value",selectedStartDate)
    const dateEndInput = document.querySelector("#end_timepicker_text");
    const selectedEndDate = dateEndInput.value;
    return [selectedStartDate,selectedEndDate]
}

function get_time_img_value(){
    const dateStartInput = document.querySelector("#start_timepicker_img");
    const selectedStartDate = dateStartInput.value;
    dateStartInput.setAttribute("value",selectedStartDate)
    const dateEndInput = document.querySelector("#end_timepicker_img");
    const selectedEndDate = dateEndInput.value;
    return [selectedStartDate,selectedEndDate]
}

function inference_job_timepicker_img_change(){
    // 获取日期选择器元素
    const dateStartInput = document.querySelector("#start_timepicker_img");
    const selectedStartDate = dateStartInput.value;
    dateStartInput.setAttribute("value",selectedStartDate)
    const dateEndInput = document.querySelector("#end_timepicker_img");
    const selectedEndDate = dateEndInput.value;
    dateEndInput.setAttribute("value",selectedEndDate)
    gradioApp().getElementById("start_time_picker_img_hidden").click()
    gradioApp().getElementById("end_time_picker_img_hidden").click()
    gradioApp().getElementById("start_time_picker_img_hidden").value = selectedStartDate
    gradioApp().getElementById("end_time_picker_img_hidden").value= selectedEndDate
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

function scrap_ui_component_value_with_default(config, ctx) {


    const getElementValue = (selector, property, defaultValue) => {
        const element = ctx.querySelector(selector);
        return element ? element[property] : defaultValue;
    };

    config["script_txt2txt_xyz_plot_x_values"] = getElementValue(
        "#script_txt2txt_xyz_plot_x_values > label > textarea",
        "value",
        ""
    );
    config["script_txt2txt_xyz_plot_y_values"] = getElementValue(
        "#script_txt2txt_xyz_plot_y_values > label > textarea",
        "value",
        ""
    );
    config["script_txt2txt_xyz_plot_z_values"] = getElementValue(
        "#script_txt2txt_xyz_plot_z_values > label > textarea",
        "value",
        ""
    );
    config["script_txt2txt_prompt_matrix_different_seeds"] = getElementValue(
        "#script_txt2txt_prompt_matrix_different_seeds > label > input",
        "checked",
        false
    );
    config["script_txt2txt_prompt_matrix_margin_size"] = getElementValue(
        "#script_txt2txt_prompt_matrix_margin_size > div > div > input",
        "value",
        ""
    );
    config["script_txt2txt_prompt_matrix_put_at_start"] = getElementValue(
        "#script_txt2txt_prompt_matrix_put_at_start > label > input",
        "checked",
        false
    );
    config["script_txt2txt_checkbox_iterate_every_line"] =
        getElementValue(
            "#script_txt2txt_prompts_from_file_or_textbox_checkbox_iterate > label > input",
            "checked",
            false
        );
    config["script_txt2txt_checkbox_iterate_all_lines"] =
        getElementValue(
            "#script_txt2txt_prompts_from_file_or_textbox_checkbox_iterate_batch > label > input",
            "checked",
            false
        );
    config["script_txt2txt_xyz_plot_draw_legend"] = getElementValue(
        "#script_txt2txt_xyz_plot_draw_legend > label > input",
        "checked",
        false
    );
    config["script_txt2txt_xyz_plot_include_lone_images"] = getElementValue(
        "#script_txt2txt_xyz_plot_include_lone_images > label > input",
        "checked",
        false
    );
    config["script_txt2txt_xyz_plot_include_sub_grids"] = getElementValue(
        "#script_txt2txt_xyz_plot_include_sub_grids > label > input",
        "checked",
        false
    );
    config["script_txt2txt_xyz_plot_margin_size"] = getElementValue(
        "#script_txt2txt_xyz_plot_margin_size > div > div > input",
        "value",
        ""
    );
    config["script_txt2txt_xyz_plot_no_fixed_seeds"] = getElementValue(
        "#script_txt2txt_xyz_plot_no_fixed_seeds > label > input",
        "checked",
        false
    );
    config["txt2img_batch_count"] = getElementValue(
        "#txt2img_batch_count > div > div > input",
        "value",
        ""
    );
    config["txt2img_batch_size"] = getElementValue(
        "#txt2img_batch_size > div > div > input",
        "value",
        ""
    );
    config["txt2img_cfg_scale"] = getElementValue(
        "#txt2img_cfg_scale > div > div > input",
        "value",
        ""
    );
    config["txt2img_denoising_strength"] = getElementValue(
        "#txt2img_denoising_strength > div > div > input",
        "value",
        ""
    );
    config["txt2img_enable_hr"] = getElementValue(
        "#txt2img_enable_hr > label > input",
        "checked",
        false
    );
    config["txt2img_height"] = getElementValue(
        "#txt2img_height > div > div > input",
        "value",
        ""
    );
    config["txt2img_hires_steps"] = getElementValue(
        "#txt2img_hires_steps > div > div > input",
        "value",
        ""
    );
    config["txt2img_hr_resize_x"] = getElementValue(
        "#txt2img_hr_resize_x > div > div > input",
        "value",
        ""
    );
    config["txt2img_hr_resize_y"] = getElementValue(
        "#txt2img_hr_resize_y > div > div > input",
        "value",
        ""
    );
    config["txt2img_hr_scale"] = getElementValue(
        "#txt2img_hr_scale > div > div > input",
        "value",
        ""
    );
    config["txt2img_restore_faces"] = getElementValue(
        "#txt2img_restore_faces > label > input",
        "checked",
        false
    );
    config["txt2img_seed"] = getElementValue(
        "#txt2img_seed > label > input",
        "value",
        ""
    );
    config["txt2img_seed_resize_from_h"] = getElementValue(
        "#txt2img_seed_resize_from_h > div > div > input",
        "value",
        ""
    );
    config["txt2img_seed_resize_from_w"] = getElementValue(
        "#txt2img_seed_resize_from_w > div > div > input",
        "value",
        ""
    );

    config["txt2img_steps"] = getElementValue(
        "#txt2img_steps > div > div > input",
        "value",
        ""
    );
    config["txt2img_subseed"] = getElementValue(
        "#txt2img_subseed > label > input",
        "value",
        ""
    );
    config["txt2img_subseed_show"] = getElementValue(
        "#txt2img_subseed_show > label > input",
        "checked",
        false
    );
    config["txt2img_subseed_strength"] = getElementValue(
        "#txt2img_subseed_strength > div > div > input",
        "value",
        ""
    );
    config["txt2img_tiling"] = getElementValue(
        "#txt2img_tiling > label > input",
        "checked",
        false
    );
    config["txt2img_width"] = getElementValue(
        "#txt2img_width > div > div > input",
        "value",
        ""
    );

    config["script_list"] = getElementValue(
        "#script_list > label > div > div.wrap-inner.svelte-aqlk7e > div > input",
        "value",
        ""
    );

    config["script_txt2txt_xyz_plot_x_type"] = getElementValue(
        "#script_txt2txt_xyz_plot_x_type > label > div > div.wrap-inner.svelte-aqlk7e > div > input",
        "value",
        ""
    );
    config["script_txt2txt_xyz_plot_x_value"] = getElementValue(
        "#script_txt2txt_xyz_plot_x_values > label > textarea",
        "value",
        ""
    );
    config["script_txt2txt_xyz_plot_y_type"] = getElementValue(
        "#script_txt2txt_xyz_plot_y_type > label > div > div.wrap-inner.svelte-aqlk7e > div > input",
        "value",
        ""
    );
    config["script_txt2txt_xyz_plot_y_value"] = getElementValue(
        "#script_txt2txt_xyz_plot_y_values > label > textarea",
        "value",
        ""
    );
    config["script_txt2txt_xyz_plot_z_type"] = getElementValue(
        "#script_txt2txt_xyz_plot_z_type > label > div > div.wrap-inner.svelte-aqlk7e > div > input",
        "value",
        ""
    );
    config["script_txt2txt_xyz_plot_z_value"] = getElementValue(
        "#script_txt2txt_xyz_plot_z_values > label > textarea",
        "value",
        ""
    );

    config["txt2img_hr_upscaler"] = getElementValue(
        "#txt2img_hr_upscaler > label > div > div > div > input",
        "value",
        ""
    );
    config["txt2img_sampling_method"] = getElementValue(
        "#txt2img_sampling > label > div > div.wrap-inner.svelte-aqlk7e > div > input",
        "value",
        ""
    );

    config["txt2img_sampling_steps"] = getElementValue(
        "#txt2img_steps > div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    );

    //sagemaker endpoint
    // config["sagemaker_endpoint"] = getElementValue(
    //     "#sagemaker_endpoint_dropdown > label > div > div.wrap-inner.svelte-aqlk7e > div > input",
    //     "value",
    //     ""
    // );
    // config["sagemaker_endpoint"] = document.querySelector("#sagemaker_endpoint_dropdown > label > div > div.wrap-inner.svelte-aqlk7e > div > input").value.split("+")[0];
    const sagemaker_ep_info = ctx.querySelector("#sagemaker_endpoint_dropdown > label > div > div.wrap-inner.svelte-aqlk7e > div > input").value;
    const sagemaker_ep_info_array = sagemaker_ep_info.split("+");
    config["sagemaker_endpoint"] = sagemaker_ep_info_array[0];

    //stable diffusion checkpoint
    const sd_checkpoint_txt2img = ctx.querySelector(
        "#stable_diffusion_checkpoint_dropdown > label > div > div.wrap-inner.svelte-aqlk7e"
    );
    const sd_tokens_txt2img = sd_checkpoint_txt2img.querySelectorAll(".token.svelte-aqlk7e");
    const sd_values_txt2img = [];

    sd_tokens_txt2img.forEach((token) => {
        const spanValue = token.querySelector("span.svelte-aqlk7e").textContent;
        sd_values_txt2img.push(spanValue);
    });
    config["txt2img_sagemaker_stable_diffusion_checkpoint"] = sd_values_txt2img.join(":");

    const sd_checkpoint_img2img = ctx.querySelector(
        "#stable_diffusion_checkpoint_dropdown > label > div > div.wrap-inner.svelte-aqlk7e"
    );
    const sd_tokens_img2img = sd_checkpoint_img2img.querySelectorAll(".token.svelte-aqlk7e");
    const sd_values_img2img = [];

    sd_tokens_img2img.forEach((token) => {
        const spanValue = token.querySelector("span.svelte-aqlk7e").textContent;
        sd_values_img2img.push(spanValue);
    });
    config["img2img_sagemaker_stable_diffusion_checkpoint"] = sd_values_img2img.join(":");

    //Textual Inversion for txt2img
    const txt2img_wrapInner = ctx.querySelector(
        "#sagemaker_texual_inversion_dropdown > label > div > div.wrap-inner.svelte-aqlk7e"
    );
    const txt2img_tokens = txt2img_wrapInner.querySelectorAll(".token.svelte-aqlk7e");
    const txt2img_values = [];

    txt2img_tokens.forEach((token) => {
        const spanValue = token.querySelector("span.svelte-aqlk7e").textContent;
        txt2img_values.push(spanValue);
    });
    config["txt2img_sagemaker_texual_inversion_model"] = txt2img_values.join(":");

    //LoRa
    const txt2img_wrapInner1 = ctx.querySelector(
        "#sagemaker_lora_list_dropdown > label > div > div.wrap-inner.svelte-aqlk7e"
    );
    const txt2img_tokens1 = txt2img_wrapInner1.querySelectorAll(".token.svelte-aqlk7e");
    const txt2img_values1 = [];

    txt2img_tokens1.forEach((token) => {
        const spanValue = token.querySelector("span.svelte-aqlk7e").textContent;
        txt2img_values1.push(spanValue);
    });
    config["txt2img_sagemaker_lora_model"] = txt2img_values1.join(":");
    console.log(txt2img_values1);

    //HyperNetwork
    const txt2img_wrapInner2 = ctx.querySelector(
        "#sagemaker_hypernetwork_dropdown > label > div > div.wrap-inner.svelte-aqlk7e"
    );
    const txt2img_tokens2 = txt2img_wrapInner2.querySelectorAll(".token.svelte-aqlk7e");
    const txt2img_values2 = [];

    txt2img_tokens2.forEach((token) => {
        const spanValue = token.querySelector("span.svelte-aqlk7e").textContent;
        txt2img_values2.push(spanValue);
    });
    config["txt2img_sagemaker_hypernetwork_model"] = txt2img_values2.join(":");
    console.log(txt2img_values2);

    //ControlNet model
    const txt2img_wrapInner3 = ctx.querySelector(
        "#sagemaker_controlnet_model_dropdown > label > div > div.wrap-inner.svelte-aqlk7e"
    );
    const txt2img_tokens3 = txt2img_wrapInner3.querySelectorAll(".token.svelte-aqlk7e");
    const txt2img_values3 = [];

    txt2img_tokens3.forEach((token) => {
        const spanValue = token.querySelector("span.svelte-aqlk7e").textContent;
        txt2img_values3.push(spanValue);
    });
    config["txt2img_sagemaker_controlnet_model"] = txt2img_values3.join(":");
    console.log(txt2img_values3);

    //Textual Inversion for img2img
    const img2img_wrapInner = ctx.querySelector(
        "#sagemaker_texual_inversion_dropdown > label > div > div.wrap-inner.svelte-aqlk7e"
    );
    const img2img_tokens = img2img_wrapInner.querySelectorAll(".token.svelte-aqlk7e");
    const img2img_values = [];

    img2img_tokens.forEach((token) => {
        const spanValue = token.querySelector("span.svelte-aqlk7e").textContent;
        img2img_values.push(spanValue);
    });
    config["img2img_sagemaker_texual_inversion_model"] = img2img_values.join(":");

    //LoRa
    const img2img_wrapInner1 = ctx.querySelector(
        "#sagemaker_lora_list_dropdown > label > div > div.wrap-inner.svelte-aqlk7e"
    );
    const img2img_tokens1 = img2img_wrapInner1.querySelectorAll(".token.svelte-aqlk7e");
    const img2img_values1 = [];

    img2img_tokens1.forEach((token) => {
        const spanValue = token.querySelector("span.svelte-aqlk7e").textContent;
        img2img_values1.push(spanValue);
    });
    config["img2img_sagemaker_lora_model"] = img2img_values1.join(":");
    console.log(img2img_values1);

    //HyperNetwork
    const img2img_wrapInner2 = ctx.querySelector(
        "#sagemaker_hypernetwork_dropdown > label > div > div.wrap-inner.svelte-aqlk7e"
    );
    const img2img_tokens2 = img2img_wrapInner2.querySelectorAll(".token.svelte-aqlk7e");
    const img2img_values2 = [];

    img2img_tokens2.forEach((token) => {
        const spanValue = token.querySelector("span.svelte-aqlk7e").textContent;
        img2img_values2.push(spanValue);
    });
    config["img2img_sagemaker_hypernetwork_model"] = img2img_values2.join(":");
    console.log(img2img_values2);

    //ControlNet model
    const img2img_wrapInner3 = ctx.querySelector(
        "#sagemaker_controlnet_model_dropdown > label > div > div.wrap-inner.svelte-aqlk7e"
    );
    const img2img_tokens3 = img2img_wrapInner3.querySelectorAll(".token.svelte-aqlk7e");
    const img2img_values3 = [];

    img2img_tokens3.forEach((token) => {
        const spanValue = token.querySelector("span.svelte-aqlk7e").textContent;
        img2img_values3.push(spanValue);
    });
    config["img2img_sagemaker_controlnet_model"] = img2img_values3.join(":");
    console.log(img2img_values3);

   //control net part parameter for txt2img
    const imgElement = ctx.querySelector(
        "#txt2img_controlnet_ControlNet_input_image > div.image-container.svelte-p3y7hu > div > img"
    );
    if (imgElement) {
        const srcValue = imgElement.getAttribute("src");
        // Use the srcValue variable as needed
        const baseImage = new Image();
        baseImage.src = srcValue;
        // 创建一个 canvas 元素
        const canvasOrg = ctx.querySelector('#txt2img_controlnet_ControlNet_input_image > div.image-container.svelte-p3y7hu > div > div.wrap.svelte-yigbas > canvas[key="drawing"]');
        const canvas = document.createElement('canvas');
        // 设置 canvas 的宽度和高度
        canvas.width = canvasOrg.width;
        canvas.height = canvasOrg.height;
        // 设置 Canvas 元素的样式，使其在页面中不可见
        canvas.style.display = 'none';
        const context = canvas.getContext('2d');
        context.drawImage(baseImage, 0, 0, canvasOrg.width, canvasOrg.height);
        const srcValueByCanvas = canvas.toDataURL();
        config["txt2img_controlnet_ControlNet_input_image_original"] = srcValueByCanvas;

        const drawingCanvas = ctx.querySelector('#txt2img_controlnet_ControlNet_input_image > div.image-container.svelte-p3y7hu > div > div.wrap.svelte-yigbas > canvas[key="drawing"]');
        if (drawingCanvas) {
            const imageDataURL = drawingCanvas.toDataURL();
            config["txt2img_controlnet_ControlNet_input_image"] = imageDataURL;
        } else {
            console.log("txt2img_controlnet_ControlNet_input_image is null")
            config["txt2img_controlnet_ControlNet_input_image"] = "";
        }
    } else {
        // Handle the case when imgElement is null or undefined
        console.log("imgElement is null or undefined");
        config["txt2img_controlnet_ControlNet_input_image"] = "";
    }

    // Start grapping controlnet related ui values of txt2img
    config["txt2img_controlnet_enable"] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_enable_checkbox > label > input",
        "checked",
        false
    );

    config["txt2img_controlnet_lowVRAM_enable"] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_low_vram_checkbox > label > input",
        "checked",
        false
    );

    config["txt2img_controlnet_pixel_perfect"] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_pixel_perfect_checkbox > label > input",
        "checked",
        false
    );

    config["txt2img_controlnet_allow_preview"] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_preprocessor_preview_checkbox > label > input",
        "checked",
        false
    );


    config["txt2img_controlnet_preprocessor"] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_preprocessor_dropdown > label > div > div.wrap-inner.svelte-aqlk7e > div > input",
        "value",
        ""
    );

    config["txt2img_controlnet_model"] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_model_dropdown > label > div > div.wrap-inner.svelte-aqlk7e > div > input",
        "value",
        ""
    );

    config["txt2img_controlnet_weight"] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_control_weight_slider > div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    );

    config["txt2img_controlnet_starting_control_step"] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_start_control_step_slider > div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    );

    config["txt2img_controlnet_ending_control_step"] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_ending_control_step_slider > div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    );

    config["txt2img_controlnet_control_mode_balanced"] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_control_mode_radio > div.wrap.svelte-1p9xokt > label:nth-child(1) > input",
        "checked",
        false
    );

    config["txt2img_controlnet_control_mode_my_prompt_is_more_important"] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_control_mode_radio > div.wrap.svelte-1p9xokt > label:nth-child(2) > input",
        "checked",
        false
    );

    config["txt2img_controlnet_control_mode_controlnet_is_more_important"] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_control_mode_radio > div.wrap.svelte-1p9xokt > label:nth-child(3) > input",
        "checked",
        false
    );

    config["txt2img_controlnet_resize_mode_just_resize"] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_resize_mode_radio > div.wrap.svelte-1p9xokt > label:nth-child(1) > input",
        "checked",
        false
    );

    config["txt2img_controlnet_resize_mode_Crop_and_Resize"] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_resize_mode_radio > div.wrap.svelte-1p9xokt > label:nth-child(2) > input",
        "checked",
        false
    );

    config["txt2img_controlnet_resize_mode_Resize_and_Fill"] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_resize_mode_radio > div.wrap.svelte-1p9xokt > label:nth-child(3) > input",
        "checked",
        false
    );

    config[
        "txt2img_controlnet_loopback_automatically"
    ] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_automatically_send_generated_images_checkbox > label > input",
        "checked",
        false
    );


    // Completed when Preprocessor is null

    // Start when Preprocessor is canny
    config["txt2img_controlnet_preprocessor_resolution"] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_preprocessor_resolution_slider> div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    )

    config["txt2img_controlnet_canny_low_threshold"] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_threshold_A_slider> div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    )

    config["txt2img_controlnet_canny_high_threshold"] = getElementValue(
        "#txt2img_controlnet_ControlNet_controlnet_threshold_B_slider> div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    )

        //control net part parameter for img2img
        const img2img_imgElement = ctx.querySelector(
            "#img2img_controlnet_ControlNet_input_image > div.image-container.svelte-p3y7hu > div > img"
        );
        if (img2img_imgElement) {
            const srcValue = img2img_imgElement.getAttribute("src");
            // Use the srcValue variable as needed
            const baseImage = new Image();
            baseImage.src = srcValue;
            const canvasOrg = ctx.querySelector('#img2img_controlnet_ControlNet_input_image > div.image-container.svelte-p3y7hu > div > div.wrap.svelte-yigbas > canvas[key="drawing"]');
            const canvas = document.createElement('canvas');
            // 设置 canvas 的宽度和高度
            canvas.width = canvasOrg.width;
            canvas.height = canvasOrg.height;
            // 设置 Canvas 元素的样式，使其在页面中不可见
            canvas.style.display = 'none';
            const context = canvas.getContext('2d');
            context.drawImage(baseImage, 0, 0, canvasOrg.width, canvasOrg.height);
            const srcValueByCanvas = canvas.toDataURL();
            config["img2img_controlnet_ControlNet_input_image_original"] = srcValueByCanvas;

            const drawingCanvas = ctx.querySelector('#img2img_controlnet_ControlNet_input_image > div.image-container.svelte-p3y7hu > div > div.wrap.svelte-yigbas > canvas[key="drawing"]');
            if (drawingCanvas) {
                const imageDataURL = drawingCanvas.toDataURL();
                config["img2img_controlnet_ControlNet_input_image"] = imageDataURL;
            } else {
                console.log("img2img_controlnet_ControlNet_input_image is null")
                config["img2img_controlnet_ControlNet_input_image"] = ""
            }
        } else {
            // Handle the case when imgElement is null or undefined
            console.log("img2img_imgElement is null or undefined");
            config["img2img_controlnet_ControlNet_input_image"] = "";
        }

        // Start grapping controlnet related ui values of txt2img
        config["img2img_controlnet_enable"] = getElementValue(
            "#img2img_controlnet_ControlNet_controlnet_enable_checkbox > label > input",
            "checked",
            false
        );

        config["img2img_controlnet_lowVRAM_enable"] = getElementValue(
            "#img2img_controlnet_ControlNet_controlnet_low_vram_checkbox > label > input",
            "checked",
            false
        );

        config["img2img_controlnet_pixel_perfect"] = getElementValue(
            "#img2img_controlnet_ControlNet_controlnet_pixel_perfect_checkbox > label > input",
            "checked",
            false
        );

        config["img2img_controlnet_allow_preview"] = getElementValue(
            "#img2img_controlnet_ControlNet_controlnet_preprocessor_preview_checkbox > label > input",
            "checked",
            false
        );


        config["img2img_controlnet_preprocessor"] = getElementValue(
            "#img2img_controlnet_ControlNet_controlnet_preprocessor_dropdown > label > div > div.wrap-inner.svelte-aqlk7e > div > input",
            "value",
            ""
        );

        config["img2img_controlnet_model"] = getElementValue(
            "#img2img_controlnet_ControlNet_controlnet_model_dropdown > label > div > div.wrap-inner.svelte-aqlk7e > div > input",
            "value",
            ""
        );

        config["img2img_controlnet_weight"] = getElementValue(
            "#img2img_controlnet_ControlNet_controlnet_control_weight_slider > div.wrap.svelte-1cl284s > div > input",
            "value",
            ""
        );

        config["img2img_controlnet_starting_control_step"] = getElementValue(
            "#img2img_controlnet_ControlNet_controlnet_start_control_step_slider > div.wrap.svelte-1cl284s > div > input",
            "value",
            ""
        );

        config["img2img_controlnet_ending_control_step"] = getElementValue(
            "#img2img_controlnet_ControlNet_controlnet_ending_control_step_slider > div.wrap.svelte-1cl284s > div > input",
            "value",
            ""
        );

        config["img2img_controlnet_control_mode_balanced"] = getElementValue(
            "#img2img_controlnet_ControlNet_controlnet_control_mode_radio > div.wrap.svelte-1p9xokt > label:nth-child(1) > input",
            "checked",
            false
        );

        config["img2img_controlnet_control_mode_my_prompt_is_more_important"] = getElementValue(
            "#img2img_controlnet_ControlNet_controlnet_control_mode_radio > div.wrap.svelte-1p9xokt > label:nth-child(2) > input",
            "checked",
            false
        );

        config["img2img_controlnet_control_mode_controlnet_is_more_important"] = getElementValue(
            "#img2img_controlnet_ControlNet_controlnet_control_mode_radio > div.wrap.svelte-1p9xokt > label:nth-child(3) > input",
            "checked",
            false
        );

        config["img2img_controlnet_resize_mode_just_resize"] = getElementValue(
            "#img2img_controlnet_ControlNet_controlnet_resize_mode_radio > div.wrap.svelte-1p9xokt > label:nth-child(1) > input",
            "checked",
            false
        );

        config["img2img_controlnet_resize_mode_Crop_and_Resize"] = getElementValue(
            "#img2img_controlnet_ControlNet_controlnet_resize_mode_radio > div.wrap.svelte-1p9xokt > label:nth-child(2) > input",
            "checked",
            false
        );

        config["img2img_controlnet_resize_mode_Resize_and_Fill"] = getElementValue(
            "#img2img_controlnet_ControlNet_controlnet_resize_mode_radio > div.wrap.svelte-1p9xokt > label:nth-child(3) > input",
            "checked",
            false
        );

        config[
            "img2img_controlnet_loopback_automatically"
        ] = getElementValue(
            "#img2img_controlnet_ControlNet_controlnet_automatically_send_generated_images_checkbox > label > input",
            "checked",
            false
        );


        // Completed when Preprocessor is null

        // Start when Preprocessor is canny
        config["img2img_controlnet_preprocessor_resolution"] = getElementValue(
            "#img2img_controlnet_ControlNet_controlnet_preprocessor_resolution_slider> div.wrap.svelte-1cl284s > div > input",
            "value",
            ""
        )

        config["img2img_controlnet_canny_low_threshold"] = getElementValue(
            "#img2img_controlnet_ControlNet_controlnet_threshold_A_slider> div.wrap.svelte-1cl284s > div > input",
            "value",
            ""
        )

        config["img2img_controlnet_canny_high_threshold"] = getElementValue(
            "#img2img_controlnet_ControlNet_controlnet_threshold_B_slider> div.wrap.svelte-1cl284s > div > input",
            "value",
            ""
        )

    // end of controlnet section

    config["script_txt2txt_prompt_matrix_prompt_type_positive"] = getElementValue(
        "#script_txt2txt_prompt_matrix_prompt_type > div.wrap.svelte-1p9xokt > label.svelte-1p9xokt.selected > input",
        "checked",
        false
    );
    config["script_txt2txt_prompt_matrix_prompt_type_negative"] = getElementValue(
        "#script_txt2txt_prompt_matrix_prompt_type > div.wrap.svelte-1p9xokt > label:nth-child(2) > input",
        "checked",
        false
    );
    config["script_txt2txt_prompt_matrix_variations_delimiter_comma"] =
        getElementValue(
            "#script_txt2txt_prompt_matrix_variations_delimiter > div.wrap.svelte-1p9xokt > label.svelte-1p9xokt.selected > input",
            "checked",
            false
        );
    config["script_txt2txt_prompt_matrix_variations_delimiter_space"] =
        getElementValue(
            "#script_txt2txt_prompt_matrix_variations_delimiter > div.wrap.svelte-1p9xokt > label:nth-child(2) > input",
            "checked",
            false
        );
    config["script_txt2txt_prompt_matrix_margin_size"] = getElementValue(
        "#script_txt2txt_prompt_matrix_margin_size > div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    );

    config["script_txt2txt_prompts_from_file_or_textbox_checkbox_iterate"] =
        getElementValue(
            "#script_txt2txt_prompts_from_file_or_textbox_checkbox_iterate > label > input",
            "enabled",
            false
        );
    config["script_txt2txt_prompts_from_file_or_textbox_checkbox_iterate_batch"] =
        getElementValue(
            "#script_txt2txt_prompts_from_file_or_textbox_checkbox_iterate_batch > label > input",
            "enabled",
            false
        );
    config["script_txt2txt_prompts_from_file_or_textbox_prompt_txt"] =
        getElementValue(
            "#script_txt2txt_prompts_from_file_or_textbox_prompt_txt > label > textarea",
            "value",
            ""
        );
    config["script_txt2txt_prompts_from_file_or_textbox_file"] = getElementValue(
        "#script_txt2txt_prompts_from_file_or_textbox_file > div.svelte-116rqfv.center.boundedheight.flex > div",
        "value",
        ""
    );

    // config for prompt area
    config["txt2img_prompt"] = getElementValue(
        "#txt2img_prompt > label > textarea",
        "value",
        ""
    );
    config["txt2img_neg_prompt"] = getElementValue(
        "#txt2img_neg_prompt > label > textarea",
        "value",
        ""
    );
    config["txt2img_styles"] = getElementValue(
        "#txt2img_styles > label > div > div > div > input",
        "value",
        ""
    );

    // get the api-gateway url and token
    config["aws_api_gateway_url"] = document.querySelector("#aws_middleware_api > label > textarea")?
        document.querySelector("#aws_middleware_api > label > textarea")["value"]: "";

    config["aws_api_token"] = document.querySelector("#aws_middleware_token > label > textarea")?
        document.querySelector("#aws_middleware_token > label > textarea")["value"]: "";


    // get the img2img component

    //document.querySelector("#img2img_prompt > label > textarea")
    config["img2img_prompt"] = getElementValue(
        "#img2img_prompt > label > textarea",
        "value",
        ""
    );

    // document.querySelector("#img2img_neg_prompt > label > textarea")
    config["img2img_neg_prompt"] = getElementValue(
        "#img2img_neg_prompt > label > textarea",
        "value",
        ""
    )
    // document.querySelector("#img2img_styles > label > div > div.wrap-inner.svelte-aqlk7e > div > input")
    config["img2img_styles"] = getElementValue(
        "#img2img_styles > label > div > div.wrap-inner.svelte-aqlk7e > div > input",
        "value",
        ""
    )


    // Resize mode
    // document.querySelector("#resize_mode > div.wrap.svelte-1p9xokt > label.svelte-1p9xokt.selected > input")
    config["img2img_resize_mode_just_resize"] = getElementValue(
        "#resize_mode > div.wrap.svelte-1p9xokt > label.svelte-1p9xokt.selected > input",
        "checked",
        false
    );
    // document.querySelector("#resize_mode > div.wrap.svelte-1p9xokt > label:nth-child(2) > input")
    config["img2img_resize_mode_crop_and_resize"] = getElementValue(
        "#resize_mode > div.wrap.svelte-1p9xokt > label:nth-child(2) > input",
        "checked",
        false
    );

    // document.querySelector("#resize_mode > div.wrap.svelte-1p9xokt > label:nth-child(3) > input")
    config["img2img_resize_mode_resize_and_fill"] = getElementValue(
        "#resize_mode > div.wrap.svelte-1p9xokt > label:nth-child(3) > input",
        "checked",
        false
    );
    // document.querySelector("#resize_mode > div.wrap.svelte-1p9xokt > label:nth-child(4) > input")
    config["img2img_resize_mode_just_resize_latent_upscale"] = getElementValue(
        "#resize_mode > div.wrap.svelte-1p9xokt > label:nth-child(4) > input",
        "checked",
        false
    );

    // img2img sampling method
    // document.querySelector("#img2img_sampling > label > div > div.wrap-inner.svelte-aqlk7e > div > input")
    config["img2img_sampling_method"] = getElementValue(
        "#img2img_sampling > label > div > div.wrap-inner.svelte-aqlk7e > div > input",
        "value",
        ""
    );

    // document.querySelector("#img2img_steps > div.wrap.svelte-1cl284s > div > input")
    config["img2img_sampling_steps"] = getElementValue(
        "#img2img_steps > div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    );

    // document.querySelector("#img2img_restore_faces > label > input")
    config["img2img_restore_faces"] = getElementValue(
        "#img2img_restore_faces > label > input",
        "checked",
        false
    );

    // document.querySelector("#img2img_tiling > label > input")
    config["img2img_tiling"] = getElementValue(
        "#img2img_tiling > label > input",
        "checked",
        false
    );

    // Resize to
    // document.querySelector("#img2img_width > div.wrap.svelte-1cl284s > div > input")
    config["img2img_width"] = getElementValue(
        "#img2img_width > div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    );

    // document.querySelector("#img2img_height > div.wrap.svelte-1cl284s > div > input")
    config["img2img_height"] = getElementValue(
        "#img2img_height > div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    );

    // document.querySelector("#img2img_batch_count > div.wrap.svelte-1cl284s > div > input")
    config["img2img_batch_count"] = getElementValue(
        "#img2img_batch_count > div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    );

    // document.querySelector("#img2img_batch_size > div.wrap.svelte-1cl284s > div > input")
    config["img2img_batch_size"] = getElementValue(
        "#img2img_batch_size > div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    );

    // document.querySelector("#img2img_cfg_scale > div.wrap.svelte-1cl284s > div > input")
    config["img2img_cfg_scale"] = getElementValue(
        "#img2img_cfg_scale > div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    );

    // document.querySelector("#img2img_denoising_strength > div.wrap.svelte-1cl284s > div > input")
    config["img2img_denoising_strength"] = getElementValue(
        "#img2img_denoising_strength > div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    );

    // document.querySelector("#img2img_seed > label > input")
    config["img2img_seed"] = getElementValue(
        "#img2img_seed > label > input",
        "value",
        ""
    );

    // document.querySelector("#img2img_subseed_show > label > input")
    config["img2img_subseed_show"] = getElementValue(
        "#img2img_subseed_show > label > input",
        "checked",
        false
    );

    // document.querySelector("#img2img_subseed > label > input")
    config["img2img_subseed"] = getElementValue(
        "#img2img_subseed > label > input",
        "value",
        ""
    );
    // document.querySelector("#img2img_subseed_strength > div.wrap.svelte-1cl284s > div > input")
    config["img2img_subseed_strength"] = getElementValue(
        "#img2img_subseed_strength > div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    );

    // document.querySelector("#img2img_seed_resize_from_w > div.wrap.svelte-1cl284s > div > input")
    config["img2img_seed_resize_from_w"] = getElementValue(
        "#img2img_seed_resize_from_w > div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    );

    // document.querySelector("#img2img_seed_resize_from_h > div.wrap.svelte-1cl284s > div > input")
    config["img2img_seed_resize_from_h"] = getElementValue(
        "#img2img_seed_resize_from_h > div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    );


    // Resize by
    // document.querySelector("#img2img_scale > div.wrap.svelte-1cl284s > div > input")
    config["img2img_scale"] = getElementValue(
        "#img2img_scale > div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    );

    // inpaint component

    // document.querySelector("#img2img_mask_blur > div.wrap.svelte-1cl284s > div > input")
    config["img2img_mask_blur"] = getElementValue(
        "#img2img_mask_blur > div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    );

    //document.querySelector("#img2img_mask_alpha > div.wrap.svelte-1cl284s > div > input")
    config["img2img_mask_alpha"] = getElementValue(
        "#img2img_mask_alpha > div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    );

    // document.querySelector("#img2img_mask_mode > div.wrap.svelte-1p9xokt > label.svelte-1p9xokt.selected > input")
    config["img2img_mask_mode_inpaint_masked"] = getElementValue(
        "#img2img_mask_mode > div.wrap.svelte-1p9xokt > label:nth-child(1) > input",
        "checked",
        false
    );

    // document.querySelector("#img2img_mask_mode > div.wrap.svelte-1p9xokt > label:nth-child(2) > input")
    config["img2img_mask_mode_inpaint_not_masked"] = getElementValue(
        "#img2img_mask_mode > div.wrap.svelte-1p9xokt > label:nth-child(2) > input",
        "checked",
        false
    );

    // document.querySelector("#img2img_inpainting_fill > div.wrap.svelte-1p9xokt > label:nth-child(1) > input")
    config["img2img_inpainting_fill_fill"] = getElementValue(
        "#img2img_inpainting_fill > div.wrap.svelte-1p9xokt > label:nth-child(1) > input",
        "checked",
        false
    );


    // document.querySelector("#img2img_inpainting_fill > div.wrap.svelte-1p9xokt > label:nth-child(2) > input")
    config["img2img_inpainting_fill_original"] = getElementValue(
        "#img2img_inpainting_fill > div.wrap.svelte-1p9xokt > label:nth-child(2) > input",
        "checked",
        false
    );

    // document.querySelector("#resize_mode > div.wrap.svelte-1p9xokt > label:nth-child(3) > input")
    config["img2img_inpainting_fill_latent_noise"] = getElementValue(
        "#img2img_inpainting_fill > div.wrap.svelte-1p9xokt > label:nth-child(3) > input",
        "checked",
        false
    );

    // document.querySelector("#resize_mode > div.wrap.svelte-1p9xokt > label:nth-child(4) > input")
    config["img2img_inpainting_fill_latent_nothing"] = getElementValue(
        "#img2img_inpainting_fill > div.wrap.sverte-1p9xokt > label:nth-child(4) > input",
        "checked",
        false
    );

    // document.querySelector("#img2img_inpaint_full_res > div.wrap.svelte-1p9xokt > label:nth-child(1) > input")
    config["img2img_inpaint_full_res_whole_picture"] = getElementValue(
        "#img2img_inpaint_full_res > div.wrap.svelte-1p9xokt > label:nth-child(1) > input",
        "checked",
        false
    );

    // document.querySelector("#img2img_inpaint_full_res > div.wrap.svelte-1p9xokt > label:nth-child(2) > input")
    config["img2img_inpaint_full_res_only_masked"] = getElementValue(
        "#img2img_inpaint_full_res > div.wrap.svelte-1p9xokt > label:nth-child(2) > input",
        "checked",
        false
    );

    // document.querySelector("#img2img_steps > div.wrap.svelte-1cl284s > div > input")
    config["img2img_steps"] = getElementValue(
        "#img2img_steps > div.wrap.svelte-1cl284s > div > input",
        "value",
        ""
    );

    // grab the img2img inpaint sketch original image
    //document.querySelector("#inpaint_sketch")
    const inpaintImgElement = ctx.querySelector(
        "#inpaint_sketch > div.image-container.svelte-p3y7hu > div > img"
    );
    if (inpaintImgElement) {
        const srcValue = inpaintImgElement.getAttribute("src");
        // Use the srcValue variable as needed
        const baseImage = new Image();
        baseImage.src = srcValue;
        const canvasOrg = ctx.querySelector('#inpaint_sketch > div.image-container.svelte-p3y7hu > div.svelte-116rqfv > div > canvas[key="drawing"]');
        const canvas = document.createElement('canvas');
        // 设置 canvas 的宽度和高度
        canvas.width = canvasOrg.width;
        canvas.height = canvasOrg.height;
        // 设置 Canvas 元素的样式，使其在页面中不可见
        canvas.style.display = 'none';
        const context = canvas.getContext('2d');
        context.drawImage(baseImage, 0, 0, canvasOrg.width, canvasOrg.height);
        const srcValueByCanvas = canvas.toDataURL();
        config["img2img_inpaint_sketch_image"] = srcValueByCanvas;
    } else {
        // Handle the case when imgElement is null or undefined
        console.log("inpaintImgElement is null or undefined");
        config["img2img_inpaint_sketch_image"] = "";
    }



    // end of img2img component






}

function put_with_xmlhttprequest(config_url, config_data) {
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open("PUT", config_url, true);

        xhr.onreadystatechange = () => {
            if (xhr.readyState === 4) {
                // Print all response headers to the console
                console.log(xhr.getAllResponseHeaders());

                if (xhr.status >= 200 && xhr.status < 300) {
                    resolve(xhr.responseText);
                } else {
                    reject(xhr.statusText);
                }
            }
        };

        xhr.onerror = () => {
            // Print all response headers to the console
            console.log(xhr.getAllResponseHeaders());
            reject("Network error");
        };

        xhr.send(config_data);
    });
}


function getPresignedUrl(remote_url, api_key, key) {
    return new Promise((resolve, reject) => {
        const apiUrl = remote_url;
        const queryParams = new URLSearchParams({
            key: key,
        });

        const xhr = new XMLHttpRequest();
        xhr.open("GET", `${apiUrl}?${queryParams}`, true);
        xhr.setRequestHeader("x-api-key", api_key);

        xhr.onload = function () {
            if (xhr.status >= 200 && xhr.status < 400) {
                resolve(xhr.responseText);
            } else {
                reject(
                    new Error(`Error fetching presigned URL: ${xhr.statusText}`)
                );
            }
        };

        xhr.onerror = function () {
            reject(new Error("Error fetching presigned URL"));
        };

        xhr.send();
    });
}

function postToApiGateway(remote_url, api_key, data, callback) {
    const apiUrl = remote_url;

    const xhr = new XMLHttpRequest();
    xhr.open("POST", apiUrl, true);
    // xhr.setRequestHeader("Content-Type", "application/json");
    xhr.setRequestHeader("x-api-key", api_key);

    xhr.onload = function () {
        if (xhr.status >= 200 && xhr.status < 400) {
            callback(null, xhr.responseText);
        } else {
            callback(
                new Error(`Error posting to API Gateway: ${xhr.statusText}`),
                null
            );
        }
    };

    xhr.onerror = function () {
        callback(new Error("Error posting to API Gateway"), null);
    };

    // Convert data object to JSON string before sending
    xhr.send(JSON.stringify(data));
}


function logout() {
    // similar behavior as an HTTP redirect
    window.location.replace(window.location.href+"logout");
}
